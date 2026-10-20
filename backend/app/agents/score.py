"""Explainable Governance Health Score.

Two numbers, never merged into one:
  health score (0-100)   starts at 100; each finding deducts severity_weight x confidence_weight, using the
                         confidence AFTER the Reliability Sentinel. No investigation can deduct more than 30 points,
                         so overlapping findings on one topic cannot dominate the score.
  evidence coverage (%)  share of rules and decision questions that could be resolved from the evidence.

Findings with insufficient evidence deduct nothing, so missing information never looks like low risk: they are
listed separately, they lower coverage, and low coverage puts a warning on the score.
Findings the Sentinel marked "unsupported" are excluded from the score and listed.

Run on a saved report:
    python -m app.agents.score .cache/analyses/<file>_sentinel.json
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

SEVERITY_WEIGHT = {"critical": 20, "high": 12, "medium": 6, "low": 2}
CONFIDENCE_WEIGHT = {"high": 1.0, "medium": 0.7, "low": 0.4, "insufficient": 0.0}
INVESTIGATION_CAP = 30.0
BANDS = ((80, "low_concern"), (60, "moderate_concern"), (40, "elevated_concern"), (0, "high_concern"))
QUESTION_CREDIT = {"answered": 1.0, "partial": 0.5, "insufficient": 0.0}
RELIABLE_COVERAGE = 75
LIMITED_COVERAGE = 50
FORMULA = ("score = 100 - sum over investigations of min(30, sum of severity_weight x confidence_weight); "
           "severity weights: critical 20, high 12, medium 6, low 2; confidence weights (after the Reliability "
           "Sentinel): high 1.0, medium 0.7, low 0.4, insufficient 0. Unsupported findings are excluded.")


def coverage(report: dict) -> dict:
    rules = [r for r in (report.get("rule_report") or {}).get("results", []) if r.get("result") != "NOT_APPLICABLE"]
    resolved = sum(1 for r in rules if r.get("result") != "INSUFFICIENT_EVIDENCE")
    analysis = report.get("analysis") or []
    credit = sum(QUESTION_CREDIT.get(a.get("status"), 0.0) for a in analysis)
    total = len(rules) + len(analysis)
    pct = round(100 * (resolved + credit) / total) if total else 0
    label = "reliable" if pct >= RELIABLE_COVERAGE else ("limited" if pct >= LIMITED_COVERAGE else "unreliable")
    return {"pct": pct, "label": label, "rules_resolved": resolved, "rules_total": len(rules),
            "questions_credit": credit, "questions_total": len(analysis)}


def health_score(report: dict) -> dict:
    factors: list[dict] = []
    excluded: list[dict] = []
    insufficient: list[dict] = []
    raw: dict[str, float] = {}

    for f in report.get("findings", []):
        sentinel = f.get("sentinel") or {}
        if sentinel.get("verdict") == "unsupported":
            excluded.append({"id": f["id"], "title": f["title"],
                             "reason": "Reliability Sentinel: the evidence does not support this finding."})
            continue
        if f["evidence_confidence"] == "insufficient":
            insufficient.append({"id": f["id"], "title": f["title"], "severity": f["risk_severity"]})
            continue
        points = round(SEVERITY_WEIGHT[f["risk_severity"]] * CONFIDENCE_WEIGHT[f["evidence_confidence"]], 2)
        raw[f["investigation"]] = raw.get(f["investigation"], 0.0) + points
        factors.append({"id": f["id"], "title": f["title"], "investigation": f["investigation"],
                        "severity": f["risk_severity"], "confidence": f["evidence_confidence"], "points": points,
                        "human_review": bool(sentinel.get("human_review"))})

    by_investigation = {inv: {"raw": round(v, 2), "deducted": round(min(v, INVESTIGATION_CAP), 2),
                              "capped": v > INVESTIGATION_CAP} for inv, v in sorted(raw.items())}
    deducted = round(sum(d["deducted"] for d in by_investigation.values()), 2)
    score = max(0, round(100 - deducted))
    band = next(name for floor, name in BANDS if score >= floor)
    cov = coverage(report)
    human = sum(1 for f in report.get("findings", []) if (f.get("sentinel") or {}).get("human_review"))

    warnings: list[str] = []
    if cov["label"] != "reliable":
        warnings.append(f"Score rests on limited evidence: only {cov['pct']}% of rules and questions could be resolved.")
    if insufficient:
        warnings.append(f"{len(insufficient)} item(s) could not be confirmed from public filings; "
                        f"they are not counted as low risk.")
    if human:
        warnings.append(f"{human} finding(s) need human review before relying on them.")

    factors.sort(key=lambda x: (-x["points"], x["id"]))
    return {"score": score, "max": 100, "band": band, "deducted": deducted, "by_investigation": by_investigation,
            "factors": factors, "insufficient_evidence": {"count": len(insufficient), "items": insufficient},
            "excluded": excluded, "coverage": cov, "human_review": human, "warnings": warnings, "formula": FORMULA}


def _main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("usage: python -m app.agents.score <saved report .json>")
        return 1
    report = json.loads(Path(argv[1]).read_text(encoding="utf-8"))
    h = health_score(report)
    c = h["coverage"]
    print(f"Governance Health Score: {h['score']}/100 ({h['band']})  deducted {h['deducted']}")
    print(f"Evidence coverage: {c['pct']}% ({c['label']}) - rules {c['rules_resolved']}/{c['rules_total']}, "
          f"questions {c['questions_credit']}/{c['questions_total']}")
    print(f"Insufficient evidence: {h['insufficient_evidence']['count']}  excluded: {len(h['excluded'])}  "
          f"human review: {h['human_review']}")
    print("by investigation:")
    for inv, d in h["by_investigation"].items():
        print(f"  {inv:17} raw {d['raw']:6}  deducted {d['deducted']:6}{'  (capped at 30)' if d['capped'] else ''}")
    print("top factors:")
    for f in h["factors"][:8]:
        print(f"  -{f['points']:5}  {f['id']:6} {f['severity']:6}/{f['confidence']:7} {f['title'][:70]}")
    for w in h["warnings"]:
        print(f"WARNING: {w}")
    return 0


if __name__ == "__main__":
    sys.exit(_main(sys.argv))