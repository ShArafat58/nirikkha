"""DuckDB analytics warehouse for cross-company / cross-year questions (no AI, no tokens).

Built from the parsed filings in backend/.cache/parsed/:
- section size changes year over year (e.g. a 10-K section that shrank sharply)
- term trends per filing (e.g. mentions of "unrealized loss" across years)

These numbers feed the Cross-Document Consistency investigation as review signals,
never as conclusions.

Run directly:
    python -m app.analytics.warehouse --build
    python -m app.analytics.warehouse --yoy 719739
    python -m app.analytics.warehouse --terms 719739
    python -m app.analytics.warehouse --terms 719739 "unrealized loss" "liquidity"
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import tempfile
from pathlib import Path

import duckdb

from app.ingest.edgar import normalize_cik
from app.ingest.parse import ParsedDocument

DEFAULT_TERMS = [
    "interest rate risk",
    "unrealized loss",
    "held-to-maturity",
    "uninsured deposit",
    "liquidity",
    "related person",
    "chief risk officer",
    "material weakness",
]

SCHEMA = """
create table filings (
    accession_no varchar primary key, cik varchar, company varchar, form varchar,
    filing_date date, report_date date
);
create table sections (
    accession_no varchar, section_key varchar, title varchar,
    page_start integer, page_end integer, n_paragraphs integer, n_chars integer
);
create table paragraphs (
    accession_no varchar, section_key varchar, idx integer, page integer, text varchar
);
"""

SECTION_COLUMNS = ("{'accession_no': 'VARCHAR', 'section_key': 'VARCHAR', 'title': 'VARCHAR', "
                   "'page_start': 'INTEGER', 'page_end': 'INTEGER', 'n_paragraphs': 'INTEGER', 'n_chars': 'INTEGER'}")
PARAGRAPH_COLUMNS = ("{'accession_no': 'VARCHAR', 'section_key': 'VARCHAR', 'idx': 'INTEGER', "
                     "'page': 'INTEGER', 'text': 'VARCHAR'}")


def db_path(cache_dir: Path) -> Path:
    return cache_dir / "analytics.duckdb"


def build(cache_dir: Path, out: Path | None = None) -> dict:
    """(Re)build the warehouse from parsed filings. Bulk-loads via temporary JSONL files (fast)."""
    out = out or db_path(cache_dir)
    if out.exists():
        out.unlink()
    con = duckdb.connect(str(out))
    con.execute(SCHEMA)
    counts = {"filings": 0, "sections": 0, "paragraphs": 0}

    with tempfile.TemporaryDirectory() as tmp:
        sections_file = Path(tmp) / "sections.jsonl"
        paragraphs_file = Path(tmp) / "paragraphs.jsonl"
        with sections_file.open("w", encoding="utf-8") as sf, paragraphs_file.open("w", encoding="utf-8") as pf:
            for path in sorted((cache_dir / "parsed").glob("*.json")):
                doc = ParsedDocument.model_validate_json(path.read_text(encoding="utf-8"))
                con.execute(
                    "insert into filings values (?, ?, ?, ?, ?, ?)",
                    [doc.accession_no, doc.cik, doc.company, doc.form, doc.filing_date, doc.report_date],
                )
                counts["filings"] += 1
                for s in doc.sections:
                    sf.write(json.dumps({
                        "accession_no": doc.accession_no, "section_key": s.key, "title": s.title,
                        "page_start": s.page_start, "page_end": s.page_end,
                        "n_paragraphs": len(s.paragraphs), "n_chars": sum(len(p.text) for p in s.paragraphs),
                    }) + "\n")
                    counts["sections"] += 1
                    for p in s.paragraphs:
                        pf.write(json.dumps({
                            "accession_no": doc.accession_no, "section_key": s.key,
                            "idx": p.index, "page": p.page, "text": p.text,
                        }) + "\n")
                        counts["paragraphs"] += 1

        if counts["sections"]:
            con.execute(
                "insert into sections select accession_no, section_key, title, page_start, page_end, n_paragraphs, n_chars "
                f"from read_json('{sections_file.as_posix()}', format = 'newline_delimited', columns = {SECTION_COLUMNS})"
            )
        if counts["paragraphs"]:
            con.execute(
                "insert into paragraphs select accession_no, section_key, idx, page, text "
                f"from read_json('{paragraphs_file.as_posix()}', format = 'newline_delimited', columns = {PARAGRAPH_COLUMNS})"
            )
    con.close()
    return counts


def section_yoy(con: duckdb.DuckDBPyConnection, cik: str, form: str = "10-K") -> list[dict]:
    """Size of each section per filing, with change vs the previous filing of the same form."""
    rows = con.execute(
        """
        with s as (
            select f.filing_date, s.section_key, any_value(s.title) as title, sum(s.n_chars) as chars
            from sections s join filings f using (accession_no)
            where f.cik = ? and f.form = ?
            group by all
        )
        select section_key, title, filing_date, chars,
               lag(chars) over (partition by section_key order by filing_date) as prev_chars
        from s
        order by section_key, filing_date
        """,
        [normalize_cik(cik), form],
    ).fetchall()
    result = []
    for key, title, filed, chars, prev in rows:
        pct = None if not prev else round(100.0 * (chars - prev) / prev, 1)
        result.append({"section_key": key, "title": title, "filing_date": filed,
                       "chars": chars, "prev_chars": prev, "change_pct": pct})
    return result


def term_pattern(term: str) -> str:
    """Case-insensitive pattern where spaces and hyphens are interchangeable."""
    words = [w for w in re.split(r"[\s\-]+", term.lower()) if w]
    return r"[\s\-]+".join(re.escape(w) for w in words)


def term_trend(con: duckdb.DuckDBPyConnection, cik: str, terms: list[str]) -> dict[str, list[dict]]:
    """Number of mentions of each term in each filing of a company."""
    result: dict[str, list[dict]] = {}
    for term in terms:
        rows = con.execute(
            """
            select f.form, f.filing_date, sum(len(regexp_extract_all(lower(p.text), ?))) as hits
            from paragraphs p join filings f using (accession_no)
            where f.cik = ?
            group by all
            order by f.form, f.filing_date
            """,
            [term_pattern(term), normalize_cik(cik)],
        ).fetchall()
        result[term] = [{"form": form, "filing_date": filed, "hits": int(hits or 0)} for form, filed, hits in rows]
    return result


def _main(argv: list[str]) -> int:
    from app.config import get_settings

    parser = argparse.ArgumentParser(description="DuckDB analytics warehouse")
    parser.add_argument("--build", action="store_true")
    parser.add_argument("--yoy", metavar="CIK")
    parser.add_argument("--terms", nargs="+", metavar="CIK_THEN_TERMS")
    args = parser.parse_args(argv[1:])

    cache_dir = get_settings().cache_dir
    if args.build:
        counts = build(cache_dir)
        print(f"Built {db_path(cache_dir).name}: {counts}")

    if not db_path(cache_dir).exists():
        print("Warehouse not built yet. Run: python -m app.analytics.warehouse --build")
        return 1
    con = duckdb.connect(str(db_path(cache_dir)), read_only=True)

    if args.yoy:
        print(f"\nSection size year over year (10-K), CIK {args.yoy}")
        for r in section_yoy(con, args.yoy):
            if r["change_pct"] is None:
                continue
            flag = "  <-- large change, review" if abs(r["change_pct"]) >= 25 and max(r["chars"], r["prev_chars"]) >= 2000 else ""
            print(f"  {r['section_key']:10} {r['filing_date']}  {r['prev_chars']:>8,} -> {r['chars']:>8,} chars  "
                  f"{r['change_pct']:+6.1f}%  {r['title'][:45]}{flag}")

    if args.terms:
        cik, terms = args.terms[0], args.terms[1:] or DEFAULT_TERMS
        print(f"\nTerm mentions per filing, CIK {cik}")
        for term, rows in term_trend(con, cik, terms).items():
            cells = "  ".join(f"{r['form']} {r['filing_date']}: {r['hits']}" for r in rows)
            print(f"  {term:20} {cells}")
    con.close()
    return 0


if __name__ == "__main__":
    sys.exit(_main(sys.argv))