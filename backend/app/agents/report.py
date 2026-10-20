"""Governance Crash-Test Report: the four sections of the plan (section 4), built deterministically.

  1. Disclosure Verification           findings with report_section "disclosure_verification"
  2. Potential Conflict-of-Interest    findings with report_section "conflict_review"
  3. Regulatory Requirement Check      every rule result (law / best practice / internal indicator kept apart)
                                       plus regulatory findings
  4. Recommended Actions               de-duplicated actions ordered by severity, human-review items first

Every item keeps its citations with an SEC EDGAR link so the analyst can open the original filing.
No model is called here.

Run on a saved report:
    python -m app.agents.report .cache/analyses/<file>_sentinel.json
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

SECTION_TITLES = {
    "disclosure_verification": "Disclosure Verification",
    "conflict_review": "Potential Conflict-of-Interest Review",
    "regulatory_check": "Regulatory Requirement Check",
    "recommended_actions": "Recommended Actions",
}
SEVERITY_ORDER = {"critical": 0, "high": 1, "medium": 2, "low": 3}
CATEGORY_ORDER = {"law": 0, "best_practice": 1, "internal_indicator": 2}
RESULT_ORDER = {"FAIL": 0, "POTENTIAL_GAP": 1, "INSUFFICIENT_EVIDENCE": 2, "PASS": 3, "NOT_APPLICABLE": 4}


def edgar_url(cik: str, accession_no: str) -> str:
    """Folder of the filing on SEC EDGAR (works for every accession number)."""
    return f"https://www.sec.gov/Archives/edgar/data/{str(cik).lstrip('0') or '0'}/{accession_no.replace('-', '')}/"


def _citation(c: dict, cik: str) -> dict:
    return {"form": c.get("form"), "accession_no": c.get("accession_no"), "filing_date": c.get("filing_date"),
            "section": c.get("section"), "page": c.get("page"), "chunk_id": c.get("chunk_id"),
            "quote": " ".join((c.get("quote") or "").split()),
            "source_url": edgar_url(cik, c["accession_no"]) if c.get("accession_no") else None}


def _item(f: dict, cik: str) -> dict:
    s = f.get("sentinel") or {}
    return {"id": f["id"], "title": f["title"], "claim": f["claim"], "investigation": f["investigation"],
            "severity": f["risk_severity"], "confidence": f["evidence_confidence"], "source": f.get("source"),
            "rule_id": f.get("rule_id"), "decision_question": f.get("decision_question"),
            "sentinel_verdict": s.get("verdict"), "human_review": bool(s.get("human_review")),
            "sentinel_checks": [c for c in s.get("checks", []) if c.get("status") in ("warn", "fail")],
            "citations": [_citation(c, cik) for c in f.get("citations", [])],
            "recommended_actions": f.get("recommended_actions", [])}


def build_sections(report: dict) -> dict:
    cik = report.get("cik", "")
    findings = report.get("findings", [])
    groups: dict[str, list[dict]] = {"disclosure_verification": [], "conflict_review": [], "regulatory_check": [],
                                     "recommended_action": []}
    for f in findings:
        groups.setdefault(f["report_section"], []).append(_item(f, cik))

    rules = sorted(
        ({"rule_id": r.get("rule_id"), "title": r.get("title"), "applicable_rule": r.get("source"),
          "category": r.get("category"), "result": r.get("result"), "confidence": r.get("confidence"),
          "rationale": r.get("rationale"), "evidence": [_citation(c, cik) for c in r.get("evidence", [])]}
         for r in (report.get("rule_report") or {}).get("results", [])),
        key=lambda r: (CATEGORY_ORDER.get(r["category"], 9), RESULT_ORDER.get(r["result"], 9), r["rule_id"] or ""))

    actions: dict[str, dict] = {}
    for f in sorted(findings, key=lambda f: (SEVERITY_ORDER[f["risk_severity"]], f["id"])):
        for a in f.get("recommended_actions", []):
            entry = actions.setdefault(a, {"action": a, "severity": f["risk_severity"], "finding_ids": []})
            entry["finding_ids"].append(f["id"])
    review = [f["id"] for f in findings if (f.get("sentinel") or {}).get("human_review")]

    return {
        "disclosure_verification": {"title": SECTION_TITLES["disclosure_verification"],
                                    "items": groups["disclosure_verification"]},
        "conflict_review": {"title": SECTION_TITLES["conflict_review"],
                            "note": "A disclosed relationship is a question to review, not evidence of misconduct.",
                            "items": groups["conflict_review"]},
        "regulatory_check": {"title": SECTION_TITLES["regulatory_check"],
                             "note": "Applicable law, best practice and internal risk indicators are kept separate.",
                             "rules": rules, "items": groups["regulatory_check"]},
        "recommended_actions": {"title": SECTION_TITLES["recommended_actions"],
                                "human_review_first": review, "actions": list(actions.values()),
                                "items": groups["recommended_action"]},
    }


def _main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("usage: python -m app.agents.report <saved report .json>")
        return 1
    report = json.loads(Path(argv[1]).read_text(encoding="utf-8"))
    s = build_sections(report)
    for key in ("disclosure_verification", "conflict_review"):
        print(f"\n== {s[key]['title']} ({len(s[key]['items'])}) ==")
        for i in s[key]["items"]:
            c = i["citations"][0] if i["citations"] else {}
            print(f"  {i['id']:6} {i['severity']:6}/{i['confidence']:12} {i['title'][:70]}")
            if c:
                print(f"         {c['form']} p.{c['page']} {c['source_url']}")
    rc = s["regulatory_check"]
    print(f"\n== {rc['title']} ({len(rc['rules'])} rules, {len(rc['items'])} findings) ==")
    for r in rc["rules"]:
        print(f"  {r['category']:13} {r['result']:22} {r['rule_id']:20} {r['applicable_rule']}")
    ra = s["recommended_actions"]
    print(f"\n== {ra['title']} ({len(ra['actions'])} actions) ==")
    print(f"  human review first: {', '.join(ra['human_review_first']) or 'none'}")
    for a in ra["actions"][:10]:
        print(f"  [{a['severity']:6}] {a['action'][:90]}  <- {', '.join(a['finding_ids'])}")
    return 0


if __name__ == "__main__":
    sys.exit(_main(sys.argv))