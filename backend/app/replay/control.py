"""Control runs for a replay: the same pipeline on a company with no known failure,
so the replay can show that the system does not flag every company.

    python -m app.replay.control svb --subject 07da9556 --control <apple-run-id>
"""
from __future__ import annotations

import argparse
import json
import sys

from app.replay.case import CASES_DIR, CaseError, load_case
from app.replay.compare import FLAG, _load_job, collect, compare, run_as_of


def _coverage(report: dict, health: dict):
    for source in (health, report):
        for key in ("coverage_pct", "coverage", "evidence_coverage"):
            v = source.get(key)
            if isinstance(v, dict):
                v = v.get("pct", v.get("percent", v.get("value")))
            if isinstance(v, (int, float)):
                return round(v * 100) if v <= 1 else round(v)
    return None


def summarise_run(case: dict, report: dict, job_id: str) -> dict:
    findings, rules = collect(report)
    by_category: dict[str, dict[str, int]] = {}
    for r in rules:
        cat = by_category.setdefault(str(r.get("category") or "other"), {})
        cat[r["result"]] = cat.get(r["result"], 0) + 1
    health = report.get("health") if isinstance(report.get("health"), dict) else {}
    patterns = compare(case, report)["summary"]
    return {
        "job": job_id,
        "company": report.get("company"),
        "cik": report.get("cik"),
        "as_of": run_as_of(report),
        "decision": report.get("decision"),
        "health_score": health.get("score"),
        "band": health.get("band"),
        "coverage_pct": _coverage(report, health),
        "findings": len(findings),
        "rules": by_category,
        "gaps": [{"rule_id": r["rule_id"], "title": r.get("title"), "result": r["result"],
                  "category": r.get("category")} for r in rules if r["result"] in FLAG],
        "pattern_matches": {k: patterns[k] for k in ("detected", "questioned", "partial", "missed")},
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Publish subject + control run summaries for a replay")
    parser.add_argument("case_id")
    parser.add_argument("--subject", required=True, help="the replay run id (prefix ok)")
    parser.add_argument("--control", required=True, action="append", help="control run id (prefix ok)")
    args = parser.parse_args()
    try:
        case = load_case(args.case_id)
        sid, sreport, _ = _load_job(args.subject, case["cik"], case["freeze_date"])
        out = {"subject": summarise_run(case, sreport, sid), "controls": []}
        for c in args.control:
            cid, creport, _ = _load_job(c, case["cik"], case["freeze_date"])
            out["controls"].append(summarise_run(case, creport, cid))
    except (CaseError, LookupError) as exc:
        print(f"ERROR: {exc}")
        return 1
    except Exception as exc:
        print(f"ERROR: could not load a run: {exc}")
        return 1
    path = CASES_DIR / case["id"] / "controls.json"
    path.write_text(json.dumps(out, indent=1, ensure_ascii=False, default=str) + "\n", encoding="utf-8", newline="\n")
    for row in [out["subject"], *out["controls"]]:
        print(f"{row['company']:<24} as of {row['as_of']}  health {row['health_score']} ({row['band']})  "
              f"coverage {row['coverage_pct']}%  gaps {len(row['gaps'])}  patterns {row['pattern_matches']}")
    print(f"published: {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())