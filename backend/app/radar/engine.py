"""Regulatory Change Radar engine: two data streams -> prioritised, evidence-linked alerts.

Stream 1 (regulatory): curated rule changes. For each watched company, find the latest filing
of the relevant form, decide whether the rule applies to it, and search that filing for the
required disclosure. Result: addressed / gap / not_yet_required / no_filing.
Stream 2 (filing): filings on EDGAR that are not yet in our database.

No LLM. Priority is a fixed rule so it can be explained and tested. Every alert waits for a
human Approve / Reject before any follow-up action counts as started.

    python -m app.radar.engine                 # all companies in the database
    python -m app.radar.engine --cik 719739 --as-of 2023-03-07 --no-edgar
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import date, timedelta
from pathlib import Path
from typing import Callable

BACKEND_DIR = Path(__file__).resolve().parents[2]
UPDATES_FILE = BACKEND_DIR / "data" / "radar" / "regulatory_updates.json"
PRIORITY_RANK = {"high": 0, "medium": 1, "low": 2}
WATCH_FORMS = ("10-K", "DEF 14A", "PRE 14A", "8-K")
NEW_FILING_WINDOW_DAYS = 365

# search(accession_numbers, regex_pattern) -> passages: dicts with accession_no, form, page, text
SearchFn = Callable[[list[str], str], list[dict]]

FOLLOW_UP = {
    "gap": "Ask the company or check its other filings for this disclosure; send to legal or compliance review if it is still missing.",
    "addressed": "Read the passage to confirm it meets the new requirement; no further action if it does.",
    "not_yet_required": "Check the next annual report or proxy for this disclosure once the rule applies.",
    "no_filing": "Insufficient evidence: ingest the company's latest filing of this form, then re-run the Radar.",
}


def load_updates(path: Path = UPDATES_FILE) -> list[dict]:
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    updates = data["updates"]
    for u in updates:
        for key in ("id", "title", "adopted", "items", "what_changed", "applies", "check", "sources"):
            if key not in u:
                raise ValueError(f"regulatory update {u.get('id')!r} is missing {key!r}")
        date.fromisoformat(u["adopted"])
        date.fromisoformat(u["check"]["applies_from"])
    return updates


def _iso(d) -> str:
    return d.isoformat() if hasattr(d, "isoformat") else str(d)[:10]


def _latest(filings: list[dict], forms: list[str], as_of: date) -> dict | None:
    rows = [f for f in filings if f["form"] in forms and _iso(f["filing_date"]) <= as_of.isoformat()]
    return max(rows, key=lambda f: _iso(f["filing_date"])) if rows else None


def _latest_each(filings: list[dict], forms: list[str], as_of: date) -> list[dict]:
    """Latest filing of each form; proxies (DEF 14A / PRE 14A) count as one form."""
    groups: dict[str, list[str]] = {}
    for f in forms:
        groups.setdefault("proxy" if f in ("DEF 14A", "PRE 14A") else f, []).append(f)
    found = [_latest(filings, g, as_of) for g in groups.values()]
    return sorted([f for f in found if f], key=lambda f: _iso(f["filing_date"]), reverse=True)


def _quote(text: str, pattern: str, width: int = 150) -> str:
    flat = " ".join(str(text).split())
    m = re.search(pattern, flat, flags=re.I)
    if not m:
        return flat[:300]
    start, end = max(0, m.start() - width), min(len(flat), m.end() + width)
    return ("..." if start else "") + flat[start:end] + ("..." if end < len(flat) else "")


def regulatory_alerts(company: dict, filings: list[dict], updates: list[dict], search: SearchFn, as_of: date) -> list[dict]:
    alerts = []
    for u in updates:
        chk = u["check"]
        latest = _latest_each(filings, chk["forms"], as_of)
        applicable = [f for f in latest if _iso(f["filing_date"]) >= chk["applies_from"]]
        target = applicable[0] if applicable else (latest[0] if latest else None)
        passage = None
        if not latest:
            status, priority = "no_filing", "medium"
        elif not applicable:
            status, priority = "not_yet_required", "low"
        else:
            hits = search([f["accession_no"] for f in applicable], chk["pattern"])
            if hits:
                h = hits[0]
                status, priority = "addressed", "low"
                target = next((f for f in applicable if f["accession_no"] == h.get("accession_no")), target)
                passage = {"form": h.get("form"), "accession_no": h.get("accession_no"), "page": h.get("page"),
                           "quote": _quote(h.get("text", ""), chk["pattern"])}
            else:
                status, priority = "gap", "high"
        alerts.append({
            "key": f"reg:{u['id']}:{company['cik']}",
            "stream": "regulatory",
            "cik": company["cik"],
            "company": company["company"],
            "title": u["title"],
            "title_bn": u.get("title_bn"),
            "what_changed_bn": u.get("what_changed_bn"),
            "priority": priority,
            "what_changed": u["what_changed"],
            "affected_items": u["items"],
            "affected_rules": u.get("rules", []),
            "applies": u["applies"],
            "applicability_note": (
                f"Applicability estimated from the filing date (rule treated as applying to filings on or after "
                f"{chk['applies_from']}). Confirm against the company's fiscal year end."
            ),
            "disclosure_to_review": None if target is None else {
                "form": target["form"], "accession_no": target["accession_no"], "filing_date": _iso(target["filing_date"])},
            "evidence": {"status": status, "passage": passage},
            "follow_up": FOLLOW_UP[status],
            "sources": u["sources"],
            "event_date": u["adopted"],
        })
    return alerts


def filing_alerts(company: dict, known_accessions: set[str], edgar_refs: list[dict]) -> list[dict]:
    alerts = []
    for ref in edgar_refs:
        if ref["accession_no"] in known_accessions or ref["form"] not in WATCH_FORMS:
            continue
        current = ref["form"] == "8-K"
        alerts.append({
            "key": f"filing:{ref['accession_no']}",
            "stream": "filing",
            "cik": company["cik"],
            "company": company["company"],
            "title": f"New {ref['form']} filed {_iso(ref['filing_date'])}",
            "priority": "high" if current else "medium",
            "what_changed": ("A current report may announce a governance event (director or officer change, "
                             "material agreement, incident)." if current else
                             "A new annual report or proxy statement is available and has not been analysed yet."),
            "affected_items": [],
            "affected_rules": [],
            "applies": "",
            "applicability_note": "",
            "disclosure_to_review": {"form": ref["form"], "accession_no": ref["accession_no"],
                                     "filing_date": _iso(ref["filing_date"]), "url": ref.get("url")},
            "evidence": {"status": "not_analysed", "passage": None},
            "follow_up": ("Read the 8-K items; if a director, officer or auditor changed, re-run the Crash-Test."
                          if current else "Ingest this filing and re-run the Crash-Test and the Radar."),
            "sources": [{"title": f"SEC EDGAR {ref['form']}", "url": ref.get("url") or ""}] if ref.get("url") else [],
            "event_date": _iso(ref["filing_date"]),
        })
    return alerts


def prioritise(alerts: list[dict]) -> list[dict]:
    """High first, then medium, then low; newest event first within a priority."""
    by_date = sorted(alerts, key=lambda a: a["event_date"], reverse=True)
    return sorted(by_date, key=lambda a: PRIORITY_RANK[a["priority"]])


def summarise(alerts: list[dict]) -> dict:
    out = {"total": len(alerts), "by_priority": {p: 0 for p in PRIORITY_RANK}, "by_stream": {}, "by_status": {}}
    for a in alerts:
        out["by_priority"][a["priority"]] += 1
        out["by_stream"][a["stream"]] = out["by_stream"].get(a["stream"], 0) + 1
        st = a["evidence"]["status"]
        out["by_status"][st] = out["by_status"].get(st, 0) + 1
    return out


# ---------- database / EDGAR wiring (used by the CLI and the API) ----------

def db_search(conn) -> SearchFn:
    from app.rules.run import phrase_search

    def search(accessions: list[str], pattern: str) -> list[dict]:
        return [{"accession_no": p.accession_no, "form": p.form, "page": p.page, "text": p.text}
                for p in phrase_search(conn, accessions, pattern, limit=1)]
    return search


def scan(ciks: list[str] | None = None, as_of: date | None = None, use_edgar: bool = True) -> list[dict]:
    from app.config import get_settings
    from app.db import connect
    from app.ingest.edgar import EdgarClient, EdgarError, normalize_cik

    as_of = as_of or date.today()
    updates = load_updates()
    alerts: list[dict] = []
    with connect() as conn:
        if ciks:
            ciks = [normalize_cik(c) for c in ciks]
        else:
            ciks = [r[0] for r in conn.execute("select distinct cik from filings order by cik").fetchall()]
        search = db_search(conn)
        for cik in ciks:
            rows = conn.execute(
                "select accession_no, form, filing_date, company from filings where cik = %s order by filing_date",
                (cik,)).fetchall()
            if not rows:
                continue
            company = {"cik": cik, "company": rows[-1][3]}
            filings = [{"accession_no": r[0], "form": r[1], "filing_date": r[2]} for r in rows]
            alerts += regulatory_alerts(company, filings, updates, search, as_of)
            if use_edgar:
                try:
                    s = get_settings()
                    with EdgarClient(s.sec_user_agent, cache_dir=s.cache_dir) as client:
                        refs = client.list_filings(cik, forms=WATCH_FORMS, per_form=1)
                    oldest = (as_of - timedelta(days=NEW_FILING_WINDOW_DAYS)).isoformat()
                    edgar = [{"accession_no": r.accession_no, "form": r.form, "filing_date": r.filing_date,
                              "url": r.url} for r in refs if oldest <= _iso(r.filing_date) <= as_of.isoformat()]
                    alerts += filing_alerts(company, {f["accession_no"] for f in filings}, edgar)
                except EdgarError as exc:
                    print(f"  EDGAR unavailable for {cik}: {exc}")
    return prioritise(alerts)


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the Regulatory Change Radar")
    parser.add_argument("--cik", action="append")
    parser.add_argument("--as-of", type=date.fromisoformat)
    parser.add_argument("--no-edgar", action="store_true")
    args = parser.parse_args()
    try:
        alerts = scan(args.cik, args.as_of, use_edgar=not args.no_edgar)
    except Exception as exc:  # database or file errors: clear message, no traceback
        print(f"ERROR: {exc}")
        return 1
    for a in alerts:
        ev = a["evidence"]
        print(f"[{a['priority'].upper():6}] {a['stream']:10} {a['company'][:24]:24} {a['title'][:46]:46} -> {ev['status']}")
        if ev.get("passage"):
            p = ev["passage"]
            print(f"           evidence: {p['form']} p.{p['page']} \"{p['quote'][:110]}\"")
    print(f"\nsummary: {summarise(alerts)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())