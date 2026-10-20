"""LLM extraction of governance relationships from filing passages, with quote verification.

For each governance-related chunk of a filing, the extract model returns relations
(DIRECTOR_OF, COMMITTEE_CHAIR, BOARD_SEAT_ELSEWHERE, RELATED_TRANSACTION, ...), each with a
short quote. The quote is checked against the passage text: relations whose quote is not
found are kept for audit but marked verified=False and never loaded into the graph.

Tables split across chunks: the tail of the previous chunk in the same section is passed as
PRECEDING CONTEXT so the model can read column headers (e.g. committee names in a nominee table).

Prompt: app/prompts/extract_governance.v2.md (v1 kept for history).
Output: backend/.cache/extracted/<accession>.json

Run directly:
    python -m app.graph.extract 0001193125-22-064940 --limit 3
    python -m app.graph.extract 0001193125-22-064940
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
from pathlib import Path
from typing import Any, Callable, Literal

from pydantic import BaseModel, ValidationError

PROMPT_VERSION = "extract_governance.v2"
PROMPT_PATH = Path(__file__).resolve().parent.parent / "prompts" / f"{PROMPT_VERSION}.md"
CONTEXT_CHARS = 900

GOVERNANCE_SECTIONS = [
    "directors", "board_committees", "audit_committee", "compensation_committee", "nominating_committee",
    "risk_oversight", "corporate_governance", "board_leadership", "related_person_transactions",
    "executive_officers", "director_independence", "director_compensation",
    "item_10", "item_13",
]

RelationType = Literal[
    "DIRECTOR_OF", "OFFICER_OF", "COMMITTEE_CHAIR", "COMMITTEE_MEMBER",
    "BOARD_SEAT_ELSEWHERE", "EMPLOYED_BY", "RELATED_TRANSACTION",
]


class Relation(BaseModel):
    person: str
    relation: RelationType
    organization: str
    title: str | None = None
    independent: bool | None = None
    amount: str | None = None
    quote: str


class ExtractedRelation(Relation):
    chunk_id: str
    accession_no: str
    section_title: str
    page_start: int | None
    page_end: int | None
    verified: bool


class Chunk(BaseModel):
    chunk_id: str
    accession_no: str
    section_key: str
    section_title: str
    page_start: int | None
    page_end: int | None
    text: str


_HONORIFIC = re.compile(r"^(mr|ms|mrs|dr|prof)\.?\s+", re.I)


def normalize_name(name: str) -> str:
    name = _HONORIFIC.sub("", name.strip())
    return re.sub(r"\s+", " ", name).strip(" .,;")


def _norm_text(s: str) -> str:
    s = s.lower().replace("\u2019", "'").replace("\u2018", "'").replace("\u201c", '"').replace("\u201d", '"')
    s = s.replace("|", " ").replace('"', "")  # table separators and quote marks do not matter for matching
    return re.sub(r"\s+", " ", s).strip()


def quote_in_text(quote: str, text: str) -> bool:
    """True if the quote (at least 8 chars) appears in the passage, ignoring case, whitespace and '|'."""
    q = _norm_text(quote).strip(" .\"'")
    return len(q) >= 8 and q in _norm_text(text)


def load_prompt(company: str) -> str:
    return PROMPT_PATH.read_text(encoding="utf-8").replace("{company}", company)


def build_messages(company: str, form: str, chunk: Chunk, context: str = "") -> list[dict[str, str]]:
    parts = [f"Filing: {company} {form}", f"Section: {chunk.section_title}"]
    if context:
        parts.append(f"PRECEDING CONTEXT (headers only, do not extract from it):\n{context}")
    parts.append(f"PASSAGE:\n{chunk.text}")
    return [{"role": "system", "content": load_prompt(company)}, {"role": "user", "content": "\n\n".join(parts)}]


def extract_chunk(complete: Callable[..., Any], company: str, form: str, chunk: Chunk,
                  context: str = "") -> tuple[list[ExtractedRelation], dict]:
    stats = {"rejected": 0, "unverified": 0, "tokens": 0}
    result = complete("extract", build_messages(company, form, chunk, context), json_mode=True, max_tokens=1200, max_wait=75)
    stats["tokens"] = result.input_tokens + result.output_tokens
    data = result.data if isinstance(result.data, dict) else {}
    items: list[ExtractedRelation] = []
    for raw in data.get("relations", []) or []:
        try:
            rel = Relation(**raw)
        except (ValidationError, TypeError):
            stats["rejected"] += 1
            continue
        verified = quote_in_text(rel.quote, chunk.text)  # evidence must be in the cited chunk itself
        if not verified:
            stats["unverified"] += 1
        items.append(ExtractedRelation(
            **rel.model_dump(), chunk_id=chunk.chunk_id, accession_no=chunk.accession_no,
            section_title=chunk.section_title, page_start=chunk.page_start, page_end=chunk.page_end,
            verified=verified,
        ))
    return items, stats


def dedupe(items: list[ExtractedRelation]) -> list[ExtractedRelation]:
    """Keep one relation per (person, relation, organization), preferring verified ones."""
    best: dict[tuple[str, str, str], ExtractedRelation] = {}
    for item in items:
        key = (normalize_name(item.person).lower(), item.relation, item.organization.strip().lower())
        if key not in best or (item.verified and not best[key].verified):
            best[key] = item
    return list(best.values())


def load_chunks(conn, accession_no: str) -> tuple[dict, list[Chunk]]:
    filing = conn.execute(
        "select accession_no, cik, company, form, filing_date from filings where accession_no = %s", (accession_no,)
    ).fetchone()
    if filing is None:
        raise ValueError(f"Filing {accession_no} is not in the database. Load it first (app.rag.store).")
    rows = conn.execute(
        "select chunk_id, accession_no, section_key, section_title, page_start, page_end, text "
        "from chunks where accession_no = %s and section_key = any(%s) order by paragraph_start",
        (accession_no, GOVERNANCE_SECTIONS),
    ).fetchall()
    meta = {"accession_no": filing[0], "cik": filing[1], "company": filing[2], "form": filing[3],
            "filing_date": filing[4].isoformat()}
    chunks = [Chunk(chunk_id=r[0], accession_no=r[1], section_key=r[2], section_title=r[3],
                    page_start=r[4], page_end=r[5], text=r[6]) for r in rows]
    return meta, chunks


def extract_filing(accession_no: str, limit: int | None = None) -> dict:
    from app.config import get_settings
    from app.db import connect
    from app.llm.client import LLMError, get_llm

    with connect() as conn:
        meta, chunks = load_chunks(conn, accession_no)
    if limit:
        chunks = chunks[:limit]

    llm = get_llm()
    all_items: list[ExtractedRelation] = []
    totals = {"chunks": len(chunks), "failed": 0, "rejected": 0, "unverified": 0, "tokens": 0}
    started = time.perf_counter()
    previous: Chunk | None = None
    for i, chunk in enumerate(chunks, start=1):
        context = previous.text[-CONTEXT_CHARS:] if previous and previous.section_key == chunk.section_key else ""
        previous = chunk
        try:
            items, stats = extract_chunk(llm.complete, meta["company"], meta["form"], chunk, context)
        except LLMError as exc:
            totals["failed"] += 1
            print(f"  [{i}/{len(chunks)}] {chunk.section_title[:40]}: FAILED ({str(exc)[:600]})")
            continue
        all_items.extend(items)
        for k in ("rejected", "unverified", "tokens"):
            totals[k] += stats[k]
        print(f"  [{i}/{len(chunks)}] {chunk.section_title[:40]:40} relations={len(items):2}  "
              f"unverified={stats['unverified']}  tokens={stats['tokens']}")

    relations = dedupe(all_items)
    out = {
        **meta,
        "prompt_version": PROMPT_VERSION,
        "stats": {**totals, "relations": len(relations),
                  "verified": sum(1 for r in relations if r.verified),
                  "seconds": round(time.perf_counter() - started, 1)},
        "relations": [r.model_dump() for r in relations],
    }
    out_dir = get_settings().cache_dir / "extracted"
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / f"{accession_no}.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    return out


def _main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Extract governance relations from a filing")
    parser.add_argument("accession_no")
    parser.add_argument("--limit", type=int, help="only the first N governance chunks (for testing)")
    args = parser.parse_args(argv[1:])

    from app.db import DatabaseError

    try:
        out = extract_filing(args.accession_no, args.limit)
    except (DatabaseError, ValueError) as exc:
        print(f"ERROR: {exc}")
        return 1
    st = out["stats"]
    print(f"\n{out['company']} {out['form']} {out['filing_date']}: chunks={st['chunks']} failed={st['failed']} "
          f"relations={st['relations']} verified={st['verified']} rejected={st['rejected']} "
          f"tokens={st['tokens']:,} time={st['seconds']}s")
    for r in out["relations"][:25]:
        mark = "OK " if r["verified"] else "?? "
        print(f"  {mark}{r['relation']:20} {r['person'][:28]:28} -> {r['organization'][:30]:30} p.{r['page_start']}")
    if len(out["relations"]) > 25:
        print(f"  ... {len(out['relations']) - 25} more in .cache/extracted/{args.accession_no}.json")
    return 0


if __name__ == "__main__":
    sys.exit(_main(sys.argv))