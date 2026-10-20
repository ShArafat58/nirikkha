from app.agents.score import health_score


def F(fid, sev, conf, inv="relationship", verdict="verified", human=False):
    return {"id": fid, "title": fid, "investigation": inv, "risk_severity": sev, "evidence_confidence": conf,
            "sentinel": {"verdict": verdict, "human_review": human}}


def R(*results):
    return {"results": [{"result": r} for r in results]}


def test_clean_report_scores_100_with_full_coverage():
    h = health_score({"findings": [], "rule_report": R("PASS", "PASS"), "analysis": [{"status": "answered"}]})
    assert h["score"] == 100 and h["band"] == "low_concern"
    assert h["coverage"]["pct"] == 100 and h["warnings"] == []


def test_severity_times_confidence():
    h = health_score({"findings": [F("A", "high", "medium"), F("B", "low", "high", inv="consistency")],
                      "rule_report": R("PASS")})
    assert h["deducted"] == 10.4 and h["score"] == 90   # 12 x 0.7 + 2 x 1.0
    assert h["factors"][0]["id"] == "A"


def test_insufficient_evidence_never_raises_the_score_but_is_listed():
    h = health_score({"findings": [F("M", "critical", "insufficient", inv="missing_evidence")],
                      "rule_report": R("PASS", "INSUFFICIENT_EVIDENCE")})
    assert h["score"] == 100
    assert h["insufficient_evidence"]["count"] == 1
    assert h["coverage"]["pct"] == 50 and h["coverage"]["label"] == "limited"
    assert any("limited evidence" in w for w in h["warnings"])
    assert any("not counted as low risk" in w for w in h["warnings"])


def test_unsupported_findings_are_excluded_and_listed():
    h = health_score({"findings": [F("X", "high", "high", verdict="unsupported")], "rule_report": R("PASS")})
    assert h["score"] == 100 and h["excluded"][0]["id"] == "X"


def test_one_investigation_cannot_deduct_more_than_30():
    h = health_score({"findings": [F(f"R{i}", "high", "high") for i in range(5)], "rule_report": R("PASS")})
    rel = h["by_investigation"]["relationship"]
    assert rel["raw"] == 60 and rel["deducted"] == 30 and rel["capped"]
    assert h["score"] == 70


def test_human_review_warning_and_partial_questions():
    h = health_score({"findings": [F("A", "medium", "low", human=True)], "rule_report": R("PASS"),
                      "analysis": [{"status": "partial"}, {"status": "insufficient"}]})
    assert h["human_review"] == 1 and any("human review" in w for w in h["warnings"])
    assert h["coverage"]["pct"] == 50   # (1 rule + 0.5 + 0) / 3