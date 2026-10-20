"""Tests for the deterministic investigation steps (reuse SVB-like facts from test_rules)."""

from datetime import date

from test_rules import svb_facts

from app.agents.findings import (
    consistency_findings, missing_evidence_findings, number_findings, regulatory_findings, relationship_findings,
)
from app.rules.engine import evaluate


def test_relationship_flags_regulator_seat_as_high_severity_without_accusation():
    findings = relationship_findings(svb_facts())
    becker = next(f for f in findings if "Greg Becker" in f.title)
    assert becker.risk_severity == "high" and becker.report_section == "conflict_review"
    assert "not evidence of misconduct" in becker.claim
    assert becker.citations and becker.citations[0].page == 10


def test_related_party_items_above_threshold_only():
    titles = [f.title for f in relationship_findings(svb_facts()) if f.title.startswith("Related-party")]
    assert len(titles) == 2 and not any("Small Vendor" in t for t in titles)


def test_consistency_separates_severity_from_confidence():
    findings = consistency_findings(svb_facts())
    market = next(f for f in findings if "Item 7A" in f.title)
    assert market.risk_severity == "high" and market.evidence_confidence == "medium"
    assert [c.accession_no for c in market.citations] == ["k22", "k23"]
    assert any("Audit Committee" in f.title for f in findings)


def test_regulatory_findings_from_rule_gaps():
    findings = regulatory_findings(evaluate(svb_facts()))
    fin = next(f for f in findings if f.rule_id == "R407_FIN_EXPERT")
    assert fin.risk_severity == "medium" and fin.report_section == "regulatory_check"


def test_missing_evidence_is_never_low_risk_by_default():
    facts = svb_facts(relations=[], relations_source=None)
    answers = [{"question": "Who approved the deposit strategy?", "hits": [{"score": -3.2}]},
               {"question": "Is there a risk committee?", "hits": [{"score": 5.0}]}]
    findings = missing_evidence_findings(evaluate(facts), facts, answers)
    assert all(f.evidence_confidence == "insufficient" for f in findings)
    assert any("Board and officer facts may have changed" in f.title for f in findings)
    assert any(f.decision_question == "Who approved the deposit strategy?" for f in findings)
    assert not any(f.decision_question == "Is there a risk committee?" for f in findings)
    stale = next(f for f in findings if "may have changed" in f.title)
    assert "Form 8-K Item 5.02" in stale.recommended_actions[0]


def test_fresh_proxy_has_no_stale_finding():
    facts = svb_facts(as_of=date(2022, 6, 1))
    findings = missing_evidence_findings(evaluate(facts), facts)
    assert not any("may have changed" in f.title for f in findings)


def test_numbering():
    findings = number_findings(relationship_findings(svb_facts()) + consistency_findings(svb_facts()))
    assert findings[0].id == "REL-1" and any(f.id == "CON-1" for f in findings)