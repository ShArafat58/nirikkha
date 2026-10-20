"""Collect facts for a company as of a date, run the Governance Rule Engine, print and save the report.

Facts come from: Supabase (filings on or before as_of), DuckDB (sections, 10-K year-over-year sizes),
the extraction file of the latest proxy (verified graph rows), and evidence passages from the latest
proxy and 10-K found two ways: a deterministic phrase search (Postgres regex with the rule's own
pattern) first, then semantic retrieval. Nothing filed after as_of is used (evidence freeze).

Run directly:
    python -m app.rules.run 719739 --as-of 2023-03-10
    python -m app.rules.run 320193
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date, timedelta

import duckdb

from app.config import get_settings
from app.db import DatabaseError, connect
from app.ingest.edgar import PROXY_FORMS, normalize_cik
from app.rules.engine import RULE_PATTERNS, Facts, Passage, evaluate

PROXY = list(PROXY_FORMS)

RULE_QUERIES: dict[str, tuple[str, list[str]]] = {
    "independence": ("board determined directors are independent director independence", PROXY),
    "rpt_policy": ("policies and procedures for review and approval of related person transactions", PROXY),
    "risk_oversight": ("board role in risk oversight and board leadership structure", PROXY),
    "financial_expert": ("audit committee financial expert", [*PROXY, "10-K"]),
    "other_directorships": ("other public company directorships held by directors", PROXY),
    "summary_compensation": ("summary compensation table named executive officers", PROXY),
    "risk_leadership_change": ("chief risk officer separation agreement transition departure interim",
                               [*PROXY, "10-K"]),
}


def phrase_search(conn, accessions: list[str], pattern: str, limit: int = 5) -> list[Passage]:
    rows = conn.execute(
        "select c.chunk_id, f.accession_no, f.form, f.filing_date, c.section_title, c.page_start, c.text "
        "from chunks c join filings f using (accession_no) "
        "where c.accession_no = any(%s) and c.section_key <> 'front_matter' and c.text ~* %s "
        "order by c.paragraph_start limit %s",
        (accessions, pattern, limit),
    ).fetchall()
    return [Passage(accession_no=r[1], form=r[2], filing_date=r[3].isoformat(), section=r[4], page=r[5],
                    chunk_id=r[0], text=r[6], score=1.0) for r in rows]


def collect_facts(cik: str, as_of: date | None = None) -> Facts:
    from app.analytics.warehouse import resolve_db, section_yoy
    from app.graph.resolve import build_rows
    from app.rag.retrieve import retrieve

    settings = get_settings()
    cik = normalize_cik(cik)
    as_of = as_of or date.today()

    with connect() as conn:
        rows = conn.execute(
            "select accession_no, form, filing_date, company from filings where cik = %s and filing_date <= %s "
            "order by filing_date", (cik, as_of),
        ).fetchall()
        if not rows:
            raise ValueError(f"No filings for CIK {cik} on or before {as_of} in the database.")
        filings = [{"accession_no": r[0], "form": r[1], "filing_date": r[2]} for r in rows]
        facts = Facts(company=rows[-1][3], cik=cik, as_of=as_of, filings=filings)
        proxy, latest_10k = facts.latest_proxy(), facts.latest("10-K")
        latest_ids = [f["accession_no"] for f in (proxy, latest_10k) if f]

        # Deterministic phrase search first (exact rule patterns in the latest proxy / 10-K).
        for key, (_, forms) in RULE_QUERIES.items():
            allowed = [f["accession_no"] for f in (proxy, latest_10k) if f and f["form"] in forms]
            facts.passages[key] = phrase_search(conn, allowed, RULE_PATTERNS[key]) if allowed else []

    # Sections and year-over-year sizes from the DuckDB warehouse (only filings on or before as_of).
    wh = resolve_db(settings.cache_dir)
    if wh is not None:
        con = duckdb.connect(str(wh), read_only=True)
        allowed = [f["accession_no"] for f in filings]
        for acc, key in con.execute(
            "select accession_no, section_key from sections where list_contains(?, accession_no)", [allowed]
        ).fetchall():
            facts.sections.setdefault(acc, set()).add(key)
        if latest_10k:
            facts.yoy = [r for r in section_yoy(con, cik) if r["filing_date"] == latest_10k["filing_date"]]
        con.close()

    # Verified relations from the latest proxy's extraction file.
    if proxy:
        path = settings.cache_dir / "extracted" / f"{proxy['accession_no']}.json"
        if path.exists():
            facts.relations = build_rows(json.loads(path.read_text(encoding="utf-8")))
            facts.relations_source = proxy["accession_no"]

    # Semantic retrieval as a second source of passages.
    before = as_of + timedelta(days=1)
    for key, (query, forms) in RULE_QUERIES.items():
        hits, _ = retrieve(query, k=8, cik=cik, before=before, forms=forms)
        facts.passages[key] += [
            Passage(accession_no=h.accession_no, form=h.form, filing_date=h.filing_date.isoformat(),
                    section=h.section_title, page=h.page_start, chunk_id=h.chunk_id, text=h.text, score=h.score)
            for h in hits if h.accession_no in latest_ids
        ]
    return facts


ICON = {"PASS": "PASS ", "POTENTIAL_GAP": "GAP  ", "FAIL": "FAIL ", "INSUFFICIENT_EVIDENCE": "INSUF"}


def _main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Run the Governance Rule Engine")
    parser.add_argument("cik")
    parser.add_argument("--as-of", type=date.fromisoformat)
    args = parser.parse_args(argv[1:])

    try:
        facts = collect_facts(args.cik, args.as_of)
    except (DatabaseError, ValueError) as exc:
        print(f"ERROR: {exc}")
        return 1
    report = evaluate(facts)

    out_dir = get_settings().cache_dir / "rules"
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / f"{facts.cik}_{facts.as_of.isoformat()}.json"
    out.write_text(json.dumps(report, indent=1, default=str), encoding="utf-8")

    print(f"{facts.company} (CIK {facts.cik}) as of {facts.as_of}  | filings used: "
          + ", ".join(f"{f['form']} {f['filing_date']}" for f in facts.filings[-4:]))
    print(f"relations from: {facts.relations_source or 'not extracted'}\n")
    for r in report["results"]:
        review = "review" if r["human_review"] else "      "
        print(f"[{ICON[r['result']]}] {r['rule_id']:30} {r['category']:18} conf={r['confidence']:6} {review}")
        print(f"         {r['rationale'][:220]}")
        if r["evidence"]:
            e = r["evidence"][0]
            quote = " ".join(e["quote"].split())[:220]
            print(f"         evidence: {e.get('form') or ''} {e['accession_no']} p.{e.get('page')} \"{quote}\"")
    for n in report["not_applicable"]:
        print(f"[N/A  ] {n['rule_id']:30} {n['reason']}")
    print(f"\nsummary: {report['summary']}\nsaved: {out}")
    return 0


if __name__ == "__main__":
    sys.exit(_main(sys.argv))