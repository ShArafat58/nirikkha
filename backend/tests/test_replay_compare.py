import pytest

from app.replay.case import load_case
from app.replay.compare import collect, compare


@pytest.fixture
def svb():
    return load_case("svb")


def _report(extra_citation=None, yoy_text="Item 7A. Quantitative and Qualitative Disclosures About Market Risk -45%"):
    cite = {"accession_no": "A10K", "form": "10-K", "filing_date": "2023-02-24", "page": 80, "quote": "q"}
    findings = [
        {"id": "F1", "title": "Interest rate exposure",
         "statement": "Large held-to-maturity portfolio with unrealized loss", "citations": [cite]},
        {"id": "F2", "title": "Funding", "statement": "possible deposit outflow pressure", "citations": [cite]},
        {"id": "F3", "title": "Unrelated", "statement": "auditor tenure is long", "citations": [cite]},
    ]
    if extra_citation:
        findings.append({"id": "F4", "title": "Leaky", "statement": "x", "citations": [extra_citation]})
    return {
        "sections": {"disclosure": {"findings": findings}, "copy": [findings[0]]},
        "rules": {"results": [
            {"rule_id": "BP_CRO", "result": "POTENTIAL_GAP", "rationale": "Chief Risk Officer role not filled"},
            {"rule_id": "R407_RISK_OVERSIGHT", "result": "PASS", "rationale": "described"},
            {"rule_id": "II_YOY_CHANGE", "result": "POTENTIAL_GAP", "rationale": yoy_text},
        ]},
    }


def _status(result):
    return {s["id"]: s["status"] for s in result["signs"]}


def test_collect_dedupes_findings_and_reads_rules():
    findings, rules = collect(_report())
    assert len(findings) == 3
    assert {r["rule_id"] for r in rules} == {"BP_CRO", "R407_RISK_OVERSIGHT", "II_YOY_CHANGE"}


def test_statuses(svb):
    st = _status(compare(svb, _report(), {"A10K"}))
    assert st["ws_interest_rate"] == "detected"         # two keywords + market-risk rule
    assert st["ws_deposit_concentration"] == "partial"  # one keyword only
    assert st["ws_cro_vacancy"] == "detected"           # linked rule is a gap
    assert st["ws_board_oversight"] == "missed"         # rule passed, no keywords
    assert st["ws_supervisory_findings"] == "not_knowable"


def test_rule_link_needs_its_keyword(svb):
    report = _report(yoy_text="Item 1A risk factors changed")
    report["sections"]["disclosure"]["findings"][0]["statement"] = "portfolio noted"
    report["sections"]["copy"] = []
    assert _status(compare(svb, report, {"A10K"}))["ws_interest_rate"] == "missed"


def test_post_freeze_citation_invalidates_replay(svb):
    leak = {"accession_no": "A8K", "form": "8-K", "filing_date": "2023-03-08"}
    result = compare(svb, _report(extra_citation=leak), {"A10K"})
    assert result["verdict"].startswith("INVALID")
    assert result["leaks"][0]["accession_no"] == "A8K"


def test_summary_counts(svb):
    s = compare(svb, _report(), {"A10K"})["summary"]
    assert s["knowable"] == 5
    assert s["detected"] + s["partial"] + s["missed"] + s["not_knowable"] == 6
    assert s["other_signals"] >= 1