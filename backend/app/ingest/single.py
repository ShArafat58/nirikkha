"""Ingest one specific filing end to end: EDGAR -> parse -> chunk -> embed -> Supabase.

For filings outside the default 10-K / DEF 14A set, e.g. a preliminary proxy
(PRE 14A) that was never followed by a definitive one.

    python -m app.ingest.single 719739 --form "PRE 14A" --before 2023-03-08
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import date

from app.config import get_settings
from app.ingest.chunk import chunk_document, local_embedder
from app.ingest.edgar import EdgarClient, EdgarError
from app.ingest.parse import parse_filing

# Proxy variants share the DEF 14A section layout, so they are parsed with its heading rules.
PROXY_FORMS = {"PRE 14A", "DEF 14A", "DEFA14A"}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Ingest a single SEC filing")
    parser.add_argument("company", help="ticker or CIK")
    parser.add_argument("--form", required=True, help='e.g. "PRE 14A"')
    parser.add_argument("--before", type=date.fromisoformat, help="only filings on or before this date")
    parser.add_argument("--accession", help="pick this accession number if several match")
    parser.add_argument("--no-store", action="store_true", help="stop before writing to Supabase")
    args = parser.parse_args(argv)

    s = get_settings()
    try:
        with EdgarClient(s.sec_user_agent, cache_dir=s.cache_dir) as client:
            cik, name = client.lookup_company(args.company)
            refs = client.list_filings(cik, forms=(args.form,), before=args.before, per_form=5)
            if args.accession:
                refs = [r for r in refs if r.accession_no == args.accession]
            if not refs:
                print(f"ERROR: no {args.form} filing found for {name} before {args.before}")
                return 1
            ref = refs[0]
            print(f"{name} (CIK {cik})")
            print(f"  {ref.form} filed {ref.filing_date}  period {ref.report_date}  {ref.accession_no}")
            print(f"  {ref.url}")
            html = client.fetch_document(ref)
    except EdgarError as exc:
        print(f"ERROR: {exc}")
        return 1

    started = time.perf_counter()
    parse_ref = ref.model_copy(update={"form": "DEF 14A"}) if ref.form in PROXY_FORMS else ref
    doc = parse_filing(html, parse_ref)
    if doc.form != ref.form:
        doc = doc.model_copy(update={"form": ref.form})  # keep the true form label
    print(f"\nparsed: pages={doc.page_count} sections={len(doc.sections)}  {time.perf_counter() - started:.1f}s")
    for sec in doc.sections:
        chars = sum(len(p.text) for p in sec.paragraphs)
        print(f"    {sec.key:30} p.{sec.page_start}-{sec.page_end}  {chars:>9,} chars  {sec.title[:55]}")

    for sub in ("parsed", "chunks", "vectors"):
        (s.cache_dir / sub).mkdir(parents=True, exist_ok=True)
    (s.cache_dir / "parsed" / f"{doc.accession_no}.json").write_text(doc.model_dump_json(), encoding="utf-8")

    started = time.perf_counter()
    chunks = chunk_document(doc, local_embedder())
    (s.cache_dir / "chunks" / f"{doc.accession_no}.jsonl").write_text(
        "\n".join(c.model_dump_json() for c in chunks), encoding="utf-8")
    print(f"chunks: {len(chunks)}  {time.perf_counter() - started:.1f}s")
    if not chunks:
        print("ERROR: no chunks produced")
        return 1

    from app.rag.embeddings import EmbeddingError, get_embedder

    started = time.perf_counter()
    try:
        with get_embedder(s) as embedder:
            vectors = embedder.embed([c.embed_text for c in chunks])
    except EmbeddingError as exc:
        print(f"ERROR: {exc}")
        return 1
    with (s.cache_dir / "vectors" / f"{doc.accession_no}.jsonl").open("w", encoding="utf-8") as f:
        for c, v in zip(chunks, vectors):
            f.write(json.dumps({"chunk_id": c.chunk_id, "embedding": v}) + "\n")
    print(f"embeddings: {len(vectors)} x {len(vectors[0])} dims  {time.perf_counter() - started:.1f}s (cost: $0)")

    if args.no_store:
        print("--no-store: skipped Supabase")
        return 0

    from app.rag.store import CHUNK_SQL, FILING_SQL, connect, to_pgvector

    rows = [(
        c.chunk_id, c.accession_no, c.section_key, c.section_title, c.page_start, c.page_end,
        c.paragraph_start, c.paragraph_end, c.context_header, c.text, c.char_count, c.content_hash,
        to_pgvector(v),
    ) for c, v in zip(chunks, vectors)]
    try:
        with connect() as conn:
            with conn.cursor() as cur:
                cur.execute(FILING_SQL, (
                    doc.accession_no, doc.cik, doc.company, doc.form, doc.filing_date, doc.report_date,
                    doc.url, doc.page_count, doc.has_page_markers,
                ))
                cur.executemany(CHUNK_SQL, rows)
            conn.commit()
    except Exception as exc:  # database errors must not crash with a traceback
        print(f"ERROR: database write failed: {exc}")
        return 1
    print(f"stored: 1 filing, {len(rows)} chunks in Supabase")
    return 0


if __name__ == "__main__":
    sys.exit(main())