from types import SimpleNamespace

from app.agents.memo import draft_memo, to_markdown
from app.llm.client import LLMError


def F(fid, verdict="verified", conf="high", sev="medium", human=False):
    return {"id": fid, "title": f"title {fid}", "claim": f"claim {fid}", "investigation": "relationship",
            "risk_severity": sev, "evidence_confidence": conf,
            "sentinel": {"verdict": verdict, "human_review": human},
            "citations": [{"accession_no": "0001193125-22-064940", "form": "DEF 14A", "page": 10, "quote": "q"}]}


REPORT = {
    "company": "SVB", "cik": "0000719739", "as_of": "2023-03-10", "decision": "deposit partnership",
    "findings": [F("REL-2", sev="high"), F("CON-3", human=True), F("REL-7"), F("REG-1"),
                 F("BAD-1", verdict="unsupported"), F("MIS-3", conf="insufficient")],
    "rule_report": {"results": [
        {"rule_id": "R404", "source": "Reg S-K Item 404(a)", "title": "Related transactions", "result": "PASS"},
        {"rule_id": "R407", "source": "Reg S-K Item 407(h)", "title": "Risk oversight", "result": "PASS"},
        {"rule_id": "BP", "source": "Governance best practice", "title": "CRO", "result": "PASS"},
    ]},
    "health": {"score": 42, "band": "elevated_concern", "coverage": {"pct": 86}},
}


def risk(ids, rules, title="r"):
    return {"title": title, "finding_ids": ids, "rules": rules, "severity": "high", "analysis": "a",
            "why_non_obvious": "w", "recommended_action": "act"}


def llm(data, seen=None):
    def complete(task, messages, **kw):
        assert task == "reason"
        if seen is not None:
            seen.append(messages[1]["content"])
        return SimpleNamespace(data=data, provider="groq", model="openai/gpt-oss-120b", input_tokens=900,
                               output_tokens=600, latency_ms=3, cached=False)
    return complete


GOOD = {"executive_summary": "s", "risks": [
    risk(["REL-2", "CON-3"], ["Reg S-K Item 407(h)"], "one"),
    risk(["REL-7", "REG-1"], ["Reg S-K Item 404(a)"], "two"),
    risk(["REL-2", "REL-7", "XYZ-9"], ["Reg S-K Item 404(a)", "Section 10(b)"], "three"),
]}


def test_complete_memo_with_verified_citations():
    seen: list[str] = []
    m = draft_memo(REPORT, llm(GOOD, seen))
    assert m["status"] == "complete" and len(m["risks"]) == 3
    third = m["risks"][2]
    assert third["finding_ids"] == ["REL-2", "REL-7"] and third["removed_ids"] == ["XYZ-9"]
    assert third["rules"] == ["Reg S-K Item 404(a)"]
    assert m["risks"][0]["needs_human_review"] is True
    assert m["risks"][0]["evidence"][0]["source_url"].endswith("/000119312522064940/")
    assert "BAD-1" not in seen[0] and "MIS-3" not in seen[0] and "Governance best practice" not in seen[0]
    assert m["evidence_gaps"] == [{"id": "MIS-3", "title": "title MIS-3"}]


def test_single_finding_and_invented_rule_are_dropped():
    data = {"executive_summary": "s", "risks": [risk(["REL-2"], ["Reg S-K Item 404(a)"], "solo"),
                                                risk(["REL-2", "CON-3"], ["Section 10(b)"], "fake rule"),
                                                risk(["BAD-1", "REL-2"], ["Reg S-K Item 404(a)"], "unsupported")]}
    m = draft_memo(REPORT, llm(data))
    assert m["risks"] == [] and m["status"] == "insufficient" and len(m["dropped"]) == 3
    assert "minimum 3" in m["status_note"]


def test_model_unavailable_does_not_crash():
    def down(task, messages, **kw):
        raise LLMError("rate limited")
    m = draft_memo(REPORT, down)
    assert m["status"] == "unavailable" and m["risks"] == []


def test_markdown_has_disclaimer_rules_and_gaps():
    md = to_markdown(draft_memo(REPORT, llm(GOOD)))
    assert "not legal advice" in md and "Reg S-K Item 407(h)" in md
    assert "Evidence gaps" in md and "depends on human review" in md

def test_intent_words_are_dropped_and_absence_is_flagged():
    bad = risk(["REL-2", "CON-3"], ["Reg S-K Item 407(h)"], "Shrinking section may conceal gaps")
    absent = {**risk(["REL-7", "REG-1"], ["Reg S-K Item 404(a)"], "gap"), "analysis": "The 10-K does not disclose it."}
    m = draft_memo(REPORT, llm({"executive_summary": "s", "risks": [bad, absent]}))
    assert any("implies intent (conceal)" in d for d in m["dropped"])
    assert [r["title"] for r in m["risks"]] == ["gap"] and m["risks"][0]["absence_claim"] is True
    assert "not found in the reviewed passages" in to_markdown(m)


def test_reviewer_notes_reach_the_memo_writer():
    seen: list[str] = []
    rep = {**REPORT, "findings": [
        {**F("MIS-1"), "sentinel": {"verdict": "needs_review", "human_review": True,
                                    "checks": [{"check": "sufficiency", "status": "warn", "detail": "absence claim"}]}},
        F("REL-2")]}
    draft_memo(rep, llm(GOOD, seen))
    assert "reviewer notes: absence claim" in seen[0]

def test_rule_meanings_reach_the_writer_and_conduct_wording_is_flagged():
    seen: list[str] = []
    wrong = {**risk(["REL-2", "CON-3"], ["Reg S-K Item 407(h)"], "w"),
             "analysis": "Item 407(h) requires board leadership to oversee risk."}
    right = {**risk(["REL-7", "REG-1"], ["Reg S-K Item 404(a)"], "r"),
             "analysis": "Item 404(a) requires disclosure of the transaction."}
    m = draft_memo(REPORT, llm({"executive_summary": "s", "risks": [wrong, right]}, seen))
    assert "Reg S-K Item 407(h): requires disclosure of the board leadership structure" in seen[0]
    assert [r["rule_wording"] for r in m["risks"]] == [True, False]

def test_required_by_item_wording_is_flagged_for_legal_review():
    r1 = {**risk(["REL-7", "REG-1"], ["Reg S-K Item 404(a)"], "x"),
          "analysis": "Transactions must be reported consistently as required by Items 404(a) and 404(b)."}
    m = draft_memo(REPORT, llm({"executive_summary": "s", "risks": [r1]}))
    assert m["risks"][0]["rule_wording"] is True and m["risks"][0]["needs_human_review"] is True
    assert "Rule wording needs legal review" in to_markdown(m)