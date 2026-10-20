from datetime import date
from types import SimpleNamespace

from app.agents.sentinel import review_findings
from app.llm.client import LLMError

FACTS = SimpleNamespace(
    cik="0000719739", company="SVB", as_of=date(2023, 3, 10),
    filings=[
        {"accession_no": "P21", "form": "DEF 14A", "filing_date": date(2021, 3, 4)},
        {"accession_no": "P22", "form": "DEF 14A", "filing_date": date(2022, 3, 4)},
        {"accession_no": "K23", "form": "10-K", "filing_date": date(2023, 2, 24)},
        {"accession_no": "LATE", "form": "10-K", "filing_date": date(2024, 2, 24)},
    ],
)


def F(fid, claim, source="llm", conf="medium", sev="medium", inv="relationship", cites=("P22",)):
    return {"id": fid, "investigation": inv, "report_section": "conflict_review", "title": fid, "claim": claim,
            "risk_severity": sev, "evidence_confidence": conf, "rule_id": None, "decision_question": None,
            "source": source, "recommended_actions": [],
            "citations": [{"accession_no": a, "form": None, "filing_date": None, "section": None, "page": 1,
                           "chunk_id": None, "quote": "Mr. Becker has also served as a director."} for a in cites]}


def report(*findings):
    return {"findings": list(findings), "summary": {"findings": len(findings)},
            "usage": {"llm_calls": 2, "input_tokens": 100, "output_tokens": 50, "cost_usd": 0.0, "calls": []}}


def judge(verdicts, seen=None):
    def complete(task, messages, **kw):
        assert task == "reason"
        if seen is not None:
            seen.append(messages[1]["content"])
        return SimpleNamespace(data={"verdicts": verdicts}, provider="groq", model="openai/gpt-oss-120b",
                               input_tokens=300, output_tokens=40, latency_ms=5, cached=False)
    return complete


def down(task, messages, **kw):
    raise LLMError("judge down")


def by_id(rep):
    return {f["id"]: f for f in rep["findings"]}


def test_absence_claim_is_downgraded_and_severity_kept():
    rep, _ = review_findings(report(F("MIS-1", "Public filings do not disclose liquidity ratios.", sev="high",
                                      inv="missing_evidence")), FACTS, judge([{"id": "MIS-1", "supported": "yes"}]))
    f = by_id(rep)["MIS-1"]
    assert f["sentinel"]["verdict"] == "downgraded"
    assert f["evidence_confidence"] == "low" and f["sentinel"]["original_confidence"] == "medium"
    assert f["risk_severity"] == "high"
    assert f["sentinel"]["human_review"] is True


def test_negative_claim_contradicted_by_deterministic_finding():
    rep, _ = review_findings(report(
        F("REL-2", "There are no disclosed ties to major shareholders."),
        F("REL-7", "Related-party transaction disclosed with BlackRock.", source="deterministic", conf="high"),
    ), FACTS, judge([{"id": "REL-2", "supported": "yes"}]))
    f = by_id(rep)
    assert f["REL-2"]["sentinel"]["verdict"] == "unsupported"
    assert f["REL-2"]["evidence_confidence"] == "insufficient"
    assert f["REL-7"]["sentinel"]["verdict"] == "verified" and f["REL-7"]["evidence_confidence"] == "high"


def test_older_filing_is_flagged_for_review():
    rep, _ = review_findings(report(F("REG-1", "Related transactions are reviewed by the Audit Committee.",
                                      inv="regulatory", cites=("P21",))), FACTS,
                             judge([{"id": "REG-1", "supported": "yes"}]))
    f = by_id(rep)["REG-1"]
    period = next(c for c in f["sentinel"]["checks"] if c["check"] == "period")
    assert period["status"] == "warn" and "2022-03-04" in period["detail"]
    assert f["sentinel"]["verdict"] == "needs_review" and f["evidence_confidence"] == "medium"


def test_judge_rejects_unsupported_claim():
    rep, usage = review_findings(report(F("REL-1", "Becker chairs the risk committee.")), FACTS,
                                 judge([{"id": "REL-1", "supported": "no", "reason": "Passage only names a board seat."}]))
    f = by_id(rep)["REL-1"]
    assert f["sentinel"]["verdict"] == "unsupported" and f["evidence_confidence"] == "insufficient"
    assert rep["usage"]["llm_calls"] == 3 and rep["usage"]["input_tokens"] == 400 and len(usage) == 1
    assert rep["summary"]["sentinel"]["unsupported"] == 1


def test_judge_unavailable_needs_human_review():
    rep, usage = review_findings(report(
        F("REL-1", "Becker serves on the Bay Area Council board."),
        F("REL-3", "Becker holds outside board seats.", source="deterministic", conf="high"),
    ), FACTS, down)
    f = by_id(rep)
    assert f["REL-1"]["sentinel"]["verdict"] == "needs_review" and f["REL-1"]["sentinel"]["human_review"]
    assert f["REL-3"]["sentinel"]["verdict"] == "verified"
    assert usage == [] and rep["summary"]["sentinel"]["judge_model"] is None


def test_citation_after_analysis_date_is_rejected():
    rep, _ = review_findings(report(F("CON-1", "Section shrank.", source="deterministic", cites=("LATE",))),
                             FACTS, judge([]))
    f = by_id(rep)["CON-1"]
    assert f["sentinel"]["verdict"] == "unsupported" and f["evidence_confidence"] == "insufficient"


def test_judge_sees_only_llm_findings_and_unknown_ids_ignored():
    seen: list[str] = []
    rep, _ = review_findings(report(
        F("REL-1", "Becker serves on the Bay Area Council board."),
        F("REL-3", "Becker holds outside board seats.", source="deterministic", conf="high"),
    ), FACTS, judge([{"id": "REL-1", "supported": "yes"}, {"id": "XYZ-9", "supported": "no"}], seen))
    assert "REL-1" in seen[0] and "REL-3" not in seen[0]
    assert by_id(rep)["REL-1"]["sentinel"]["verdict"] == "verified"
    assert rep["summary"]["sentinel"]["verified"] == 2

def test_omit_and_lack_count_as_absence_claims():
    from app.agents.sentinel import ABSENCE
    assert ABSENCE.search("Public filings omit liquidity ratios")
    assert ABSENCE.search("the 10-K lacks a table") and ABSENCE.search("the absence of an audit")
    assert ABSENCE.search("undisclosed related-party transactions")
    assert not ABSENCE.search("Becker serves on the board")