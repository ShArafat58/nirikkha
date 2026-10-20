from app.agents.report import build_sections, edgar_url


def F(fid, section, sev="medium", actions=(), human=False, cites=()):
    return {"id": fid, "title": fid, "claim": "c", "investigation": "relationship", "report_section": section,
            "risk_severity": sev, "evidence_confidence": "high", "source": "deterministic",
            "sentinel": {"verdict": "verified", "human_review": human, "checks": []},
            "recommended_actions": list(actions),
            "citations": [{"accession_no": a, "form": "DEF 14A", "page": 10, "quote": " a  b "} for a in cites]}


REPORT = {
    "cik": "0000719739",
    "findings": [
        F("REL-1", "conflict_review", "high", ["Confirm role."], human=True, cites=["0001193125-22-064940"]),
        F("REL-2", "disclosure_verification", "medium", ["Confirm role.", "Verify approval."]),
        F("MIS-1", "recommended_action", "low", ["Ask the company."]),
    ],
    "rule_report": {"results": [
        {"rule_id": "BP_CRO", "category": "best_practice", "result": "PASS", "source": "Best practice"},
        {"rule_id": "R404_POLICY", "category": "law", "result": "PASS", "source": "Reg S-K 404(b)"},
        {"rule_id": "R407_FIN_EXPERT", "category": "law", "result": "POTENTIAL_GAP", "source": "Reg S-K 407(d)(5)"},
    ]},
}


def test_edgar_url():
    assert edgar_url("0000719739", "0001193125-22-064940") == \
        "https://www.sec.gov/Archives/edgar/data/719739/000119312522064940/"


def test_findings_go_to_their_sections_with_links():
    s = build_sections(REPORT)
    assert [i["id"] for i in s["conflict_review"]["items"]] == ["REL-1"]
    assert [i["id"] for i in s["disclosure_verification"]["items"]] == ["REL-2"]
    assert [i["id"] for i in s["recommended_actions"]["items"]] == ["MIS-1"]
    c = s["conflict_review"]["items"][0]["citations"][0]
    assert c["source_url"].endswith("/000119312522064940/") and c["quote"] == "a b"
    assert "not evidence of misconduct" in s["conflict_review"]["note"]


def test_rules_ordered_law_first_gaps_first():
    rules = build_sections(REPORT)["regulatory_check"]["rules"]
    assert [r["rule_id"] for r in rules] == ["R407_FIN_EXPERT", "R404_POLICY", "BP_CRO"]


def test_actions_deduplicated_by_severity_with_human_review_first():
    ra = build_sections(REPORT)["recommended_actions"]
    assert ra["human_review_first"] == ["REL-1"]
    assert ra["actions"][0] == {"action": "Confirm role.", "severity": "high", "finding_ids": ["REL-1", "REL-2"]}
    assert [a["action"] for a in ra["actions"]] == ["Confirm role.", "Verify approval.", "Ask the company."]