"""Load parsed filings, chunks and vectors from the local cache into Supabase Postgres.

Upserts, so it is safe to run again. Chunks without a vector are skipped (and counted).

Run directly:
    python -m app.rag.store
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

from app.db import DatabaseError, connect
from app.ingest.parse import ParsedDocument


def to_pgvector(vector: list[float]) -> str:
    return "[" + ",".join(f"{x:.6f}" for x in vector) + "]"


FILING_SQL = """
insert into filings (accession_no, cik, company, form, filing_date, report_date, url, page_count, has_page_markers)
values (%s, %s, %s, %s, %s, %s, %s, %s, %s)
on conflict (accession_no) do update set
    cik = excluded.cik, company = excluded.company, form = excluded.form,
    filing_date = excluded.filing_date, report_date = excluded.report_date, url = excluded.url,
    page_count = excluded.page_count, has_page_markers = excluded.has_page_markers
"""

CHUNK_SQL = """
insert into chunks (chunk_id, accession_no, section_key, section_title, page_start, page_end,
                    paragraph_start, paragraph_end, context_header, text, char_count, content_hash, embedding)
values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s::vector)
on conflict (chunk_id) do update set
    section_key = excluded.section_key, section_title = excluded.section_title,
    page_start = excluded.page_start, page_end = excluded.page_end,
    paragraph_start = excluded.paragraph_start, paragraph_end = excluded.paragraph_end,
    context_header = excluded.context_header, text = excluded.text, char_count = excluded.char_count,
    content_hash = excluded.content_hash, embedding = excluded.embedding
"""


def _read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def load_all(cache_dir: Path) -> dict:
    parsed_dir, chunk_dir, vector_dir = cache_dir / "parsed", cache_dir / "chunks", cache_dir / "vectors"
    stats = {"filings": 0, "chunks": 0, "skipped_no_vector": 0}

    with connect() as conn:
        with conn.cursor() as cur:
            for vector_path in sorted(vector_dir.glob("*.jsonl")):
                accession = vector_path.stem
                parsed_path = parsed_dir / f"{accession}.json"
                chunk_path = chunk_dir / f"{accession}.jsonl"
                if not parsed_path.exists() or not chunk_path.exists():
                    continue
                doc = ParsedDocument.model_validate_json(parsed_path.read_text(encoding="utf-8"))
                cur.execute(FILING_SQL, (
                    doc.accession_no, doc.cik, doc.company, doc.form, doc.filing_date, doc.report_date,
                    doc.url, doc.page_count, doc.has_page_markers,
                ))
                stats["filings"] += 1

                vectors = {row["chunk_id"]: row["embedding"] for row in _read_jsonl(vector_path)}
                rows = []
                for c in _read_jsonl(chunk_path):
                    vector = vectors.get(c["chunk_id"])
                    if vector is None:
                        stats["skipped_no_vector"] += 1
                        continue
                    rows.append((
                        c["chunk_id"], c["accession_no"], c["section_key"], c["section_title"],
                        c["page_start"], c["page_end"], c["paragraph_start"], c["paragraph_end"],
                        c["context_header"], c["text"], c["char_count"], c["content_hash"], to_pgvector(vector),
                    ))
                cur.executemany(CHUNK_SQL, rows)
                stats["chunks"] += len(rows)
                print(f"  {doc.company[:22]:22} {doc.form:8} {doc.filing_date}  chunks loaded={len(rows)}")
        conn.commit()
    return stats


def _main(argv: list[str]) -> int:
    from app.config import get_settings

    started = time.perf_counter()
    try:
        stats = load_all(get_settings().cache_dir)
    except DatabaseError as exc:
        print(f"ERROR: {exc}")
        return 1
    print(f"Loaded {stats['filings']} filings, {stats['chunks']} chunks "
          f"(skipped without vector: {stats['skipped_no_vector']}) in {time.perf_counter() - started:.1f}s")
    return 0


if __name__ == "__main__":
    sys.exit(_main(sys.argv))