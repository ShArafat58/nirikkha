from datetime import date

from app.replay.case import load_case
from app.replay.control import summarise_run
from app.rules.engine import RULES, Facts, evaluate


def test_summarise_run_counts_rules_and_patterns():
    report = {
        "company": "Control Co", "cik": "1", "as_of": "2026-10-21",
        "health": {"score": 87, "band": "low_concern", "coverage": 0.83},
        "findings": [{"id": "F1", "title": "Auditor tenure", "citations": [{"accession_no": "A"}]}],
        "rules": {"results": [
            {"rule_id": "R407_INDEPENDENCE", "result": "PASS", "category": "law", "title": "Independence"},
            {"rule_id": "BP_CRO", "result": "POTENTIAL_GAP", "category": "best_practice", "title": "CRO"},
        ]},
    }
    s = summarise_run(load_case("svb"), report, "job-1")
    assert s["health_score"] == 87 and s["coverage_pct"] == 83
    assert s["rules"] == {"law": {"PASS": 1}, "best_practice": {"POTENTIAL_GAP": 1}}
    assert [g["rule_id"] for g in s["gaps"]] == ["BP_CRO"]
    assert set(s["pattern_matches"]) == {"detected", "questioned", "partial", "missed"}


def test_cro_rule_not_applicable_outside_finance(monkeypatch):
    import app.rules.sector as sector
    monkeypatch.setattr(sector, "is_financial", lambda cik: False)
    facts = Facts(company="Tech Co", cik="0000320193", as_of=date(2026, 10, 21),
                  filings=[{"accession_no": "P", "form": "DEF 14A", "filing_date": date(2026, 1, 8)}])
    report = evaluate(facts, [r for r in RULES if r.id == "BP_CRO"])
    assert report["results"] == []
    assert report["not_applicable"][0]["rule_id"] == "BP_CRO"