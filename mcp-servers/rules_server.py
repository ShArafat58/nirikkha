"""nirikkha-rules: the Governance Rule Engine (SEC Reg S-K 401/402/404/407, best practice, internal indicators)."""
import os
import sys
from datetime import date

from mcp.server.fastmcp import FastMCP

from common import ROOT, run

mcp = FastMCP("nirikkha-rules", port=8102)


def _engine():
    """Load the backend's rule engine (needs backend/.env and its virtual environment's packages)."""
    backend = ROOT / "backend"
    if str(backend) not in sys.path:
        sys.path.insert(0, str(backend))
    os.chdir(backend)
    from app.rules import engine, run as rules_run
    return engine, rules_run


@mcp.tool()
def list_rules() -> list[dict]:
    """All rules: id, category (law, best_practice, internal_indicator), source and requirement."""
    try:
        engine, _ = _engine()
    except Exception as exc:
        return [{"error": f"Rule engine not available: {exc}"}]
    return [{"id": r.id, "category": r.category, "source": r.source, "title": r.title,
             "requirement": r.requirement} for r in engine.RULES]


@mcp.tool()
def evaluate_rules(cik: str, as_of: str | None = None) -> dict:
    """Run every rule for a company using only filings on or before as_of (YYYY-MM-DD, default today).

    Results are Pass, Potential gap, Fail or Insufficient evidence, each with its evidence passage.
    """
    try:
        engine, rules_run = _engine()
        facts = rules_run.collect_facts(cik, date.fromisoformat(as_of) if as_of else None)
        report = engine.evaluate(facts)
    except Exception as exc:
        return {"error": f"Could not evaluate rules: {exc}"}
    return {
        "company": report["company"], "as_of": report["as_of"], "summary": report["summary"],
        "results": [{"rule_id": r["rule_id"], "result": r["result"], "confidence": r["confidence"],
                     "human_review": r["human_review"], "rationale": r["rationale"],
                     "evidence": [{k: e.get(k) for k in ("form", "accession_no", "page", "quote")} for e in r["evidence"][:1]]}
                    for r in report["results"]],
        "not_applicable": report["not_applicable"],
    }


if __name__ == "__main__":
    run(mcp)