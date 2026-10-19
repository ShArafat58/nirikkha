"""Section-aware semantic chunking with contextual headers.

1. Never cross a section boundary (Item 1A stays Item 1A).
2. Inside a section, find topic shifts: embed each paragraph with a small local
   model and cut where consecutive paragraphs are least similar (semantic chunking).
3. Respect size limits (MIN_CHARS..MAX_CHARS); oversized paragraphs are split by sentence.
4. Prepend a contextual header (company, form, filing date, section, pages) to the
   text that is embedded for retrieval (contextual chunking).
5. Exact duplicate chunk texts are embedded once (saves tokens).

Run directly (reads backend/.cache/parsed/*.json, writes backend/.cache/chunks/*.jsonl):
    python -m app.ingest.chunk
    python -m app.ingest.chunk --no-semantic
"""

from __future__ import annotations

import hashlib
import math
import re
import sys
import time
from typing import Callable

from pydantic import BaseModel

from app.ingest.parse import ParsedDocument, Paragraph, Section

MIN_CHARS = 600
TARGET_CHARS = 1800
MAX_CHARS = 3200
BREAK_PERCENTILE = 0.85
EMBED_INPUT_CHARS = 400
# Mostly numeric tables: split by size only (semantic boundaries add little and cost a lot of CPU).
SIZE_ONLY_SECTIONS = {"front_matter", "item_8", "item_15"}

Embedder = Callable[[list[str]], list[list[float]]]

_SENTENCE_END = re.compile(r"(?<=[.!?;])\s+")


class Chunk(BaseModel):
    chunk_id: str
    accession_no: str
    cik: str
    company: str
    form: str
    filing_date: str
    report_date: str | None
    section_key: str
    section_title: str
    page_start: int | None
    page_end: int | None
    paragraph_start: int
    paragraph_end: int
    text: str
    context_header: str
    embed_text: str
    char_count: int
    content_hash: str


def _cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    return dot / (na * nb) if na and nb else 0.0


def _split_oversized(p: Paragraph) -> list[Paragraph]:
    """Split a paragraph longer than MAX_CHARS into sentence-packed pieces (same index and page)."""
    if len(p.text) <= MAX_CHARS:
        return [p]
    pieces: list[str] = []
    current = ""
    for sentence in _SENTENCE_END.split(p.text):
        while len(sentence) > MAX_CHARS:  # a single huge "sentence" (e.g. a table row): hard cut
            if current:
                pieces.append(current)
                current = ""
            pieces.append(sentence[:MAX_CHARS])
            sentence = sentence[MAX_CHARS:]
        if current and len(current) + 1 + len(sentence) > MAX_CHARS:
            pieces.append(current)
            current = sentence
        else:
            current = f"{current} {sentence}".strip()
    if current:
        pieces.append(current)
    return [Paragraph(index=p.index, page=p.page, text=piece) for piece in pieces]


def _semantic_breaks(paras: list[Paragraph], embed: Embedder) -> set[int]:
    """Positions i where a new chunk may start (topic shift between paragraph i-1 and i)."""
    if len(paras) < 3:
        return set()
    vectors = embed([p.text[:EMBED_INPUT_CHARS] for p in paras])
    distances = [1.0 - _cosine(vectors[i - 1], vectors[i]) for i in range(1, len(paras))]
    threshold = sorted(distances)[int(BREAK_PERCENTILE * (len(distances) - 1))]
    return {i for i, d in zip(range(1, len(paras)), distances) if d >= threshold and d > 0}


def _pack(paras: list[Paragraph], breaks: set[int], min_size: int) -> list[list[Paragraph]]:
    groups: list[list[Paragraph]] = []
    current: list[Paragraph] = []
    size = 0
    for i, p in enumerate(paras):
        length = len(p.text) + 1
        if current and (size + length > MAX_CHARS or (i in breaks and size >= min_size)):
            groups.append(current)
            current, size = [], 0
        current.append(p)
        size += length
    if current:
        last_size = sum(len(x.text) + 1 for x in groups[-1]) if groups else 0
        if groups and size < MIN_CHARS // 2 and last_size + size <= MAX_CHARS:
            groups[-1].extend(current)  # merge a tiny tail into the previous chunk
        else:
            groups.append(current)
    return groups


def context_header(doc: ParsedDocument, section: Section, page_start: int | None, page_end: int | None) -> str:
    period = f", period {doc.report_date}" if doc.report_date else ""
    if page_start is None:
        pages = "pages n/a"
    elif page_start == page_end:
        pages = f"page {page_start}"
    else:
        pages = f"pages {page_start}-{page_end}"
    return f"{doc.company} | {doc.form} filed {doc.filing_date}{period} | {section.title} | {pages}"


def chunk_document(doc: ParsedDocument, embed: Embedder | None = None) -> list[Chunk]:
    chunks: list[Chunk] = []
    seen: set[str] = set()
    for s_i, section in enumerate(doc.sections):
        paras = [piece for p in section.paragraphs for piece in _split_oversized(p)]
        if not paras:
            continue
        if embed is not None and section.key not in SIZE_ONLY_SECTIONS:
            breaks, min_size = _semantic_breaks(paras, embed), MIN_CHARS
        else:
            breaks, min_size = set(range(len(paras))), TARGET_CHARS  # size-only fallback
        for g_i, group in enumerate(_pack(paras, breaks, min_size)):
            text = "\n".join(p.text for p in group)
            digest = hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]
            if digest in seen:
                continue
            seen.add(digest)
            pages = [p.page for p in group if p.page is not None]
            page_start, page_end = (min(pages), max(pages)) if pages else (None, None)
            header = context_header(doc, section, page_start, page_end)
            chunks.append(Chunk(
                chunk_id=f"{doc.accession_no}:{s_i:03d}:{g_i:03d}",
                accession_no=doc.accession_no,
                cik=doc.cik,
                company=doc.company,
                form=doc.form,
                filing_date=doc.filing_date.isoformat(),
                report_date=doc.report_date.isoformat() if doc.report_date else None,
                section_key=section.key,
                section_title=section.title,
                page_start=page_start,
                page_end=page_end,
                paragraph_start=group[0].index,
                paragraph_end=group[-1].index,
                text=text,
                context_header=header,
                embed_text=f"{header}\n\n{text}",
                char_count=len(text),
                content_hash=digest,
            ))
    return chunks


def local_embedder(model_name: str = "BAAI/bge-small-en-v1.5") -> Embedder:
    """Small CPU embedding model (fastembed / ONNX), used only to find topic shifts."""
    from fastembed import TextEmbedding

    model = TextEmbedding(model_name=model_name)

    def embed(texts: list[str]) -> list[list[float]]:
        return [[float(x) for x in vector] for vector in model.embed(texts, batch_size=64)]

    return embed


def _main(argv: list[str]) -> int:
    from app.config import get_settings

    settings = get_settings()
    parsed_dir = settings.cache_dir / "parsed"
    out_dir = settings.cache_dir / "chunks"
    out_dir.mkdir(parents=True, exist_ok=True)
    files = sorted(parsed_dir.glob("*.json"))
    if not files:
        print(f"No parsed filings in {parsed_dir}. Run: python -m app.ingest.parse <TICKER|CIK>")
        return 1

    embed = None if "--no-semantic" in argv else local_embedder()
    print(f"Chunking {len(files)} filings ({'size-only' if embed is None else 'semantic'})")
    for path in files:
        started = time.perf_counter()
        doc = ParsedDocument.model_validate_json(path.read_text(encoding="utf-8"))
        chunks = chunk_document(doc, embed)
        out = out_dir / f"{doc.accession_no}.jsonl"
        out.write_text("\n".join(c.model_dump_json() for c in chunks), encoding="utf-8")
        sizes = [c.char_count for c in chunks] or [0]
        print(f"  {doc.company[:22]:22} {doc.form:8} {doc.filing_date}  chunks={len(chunks):4}  "
              f"avg={sum(sizes) // len(sizes):5} min={min(sizes):5} max={max(sizes):5} chars  "
              f"{time.perf_counter() - started:5.1f}s")
    return 0


if __name__ == "__main__":
    sys.exit(_main(sys.argv))