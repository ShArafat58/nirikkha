"""nirikkha-crashtest: start a Governance Crash-Test, read its report, and read the SVB Replay result."""
import os

from mcp.server.fastmcp import FastMCP

from common import api, run

mcp = FastMCP("nirikkha-crashtest", port=8104)


def _token() -> str | None:
    tok = os.getenv("NIRIKKHA_TOKEN") or None
    if tok:
        return tok
    demo = api("POST", "/api/auth/demo")
    return demo.get("token") if isinstance(demo, dict) else None


@mcp.tool()
def get_report_summary(crash_test_id: str, max_findings: int = 8) -> dict:
    """Health score, band, coverage and the top findings (with citations) of a finished Crash-Test."""
    job = api("GET", f"/api/crash-tests/{crash_test_id}")
    if "error" in job:
        return job
    rep = job.get("report") or {}
    if not rep:
        return {"status": job.get("status"), "note": "The Crash-Test has not finished yet."}
    findings = rep.get("findings") or []
    return {
        "status": job.get("status"), "company": rep.get("company"), "as_of": rep.get("as_of"), "decision": rep.get("decision"),
        "health": {k: (rep.get("health") or {}).get(k) for k in ("score", "band", "formula")},
        "findings": [{"id": f.get("id"), "title": f.get("title"), "severity": f.get("severity"), "confidence": f.get("confidence"),
                      "citation": (f.get("citations") or [{}])[0]} for f in findings[:max(1, min(max_findings, 30))]],
        "report_url": f"/report/{crash_test_id}",
    }


@mcp.tool()
def start_crash_test(cik: str, decision: str, as_of: str | None = None) -> dict:
    """Queue a Crash-Test for a decision (e.g. 'Before we invest in this company...'). Uses evidence on or before as_of."""
    token = _token()
    if not token:
        return {"error": "Could not sign in (set NIRIKKHA_TOKEN or enable the demo account)."}
    body = {"cik": cik, "decision": decision, "as_of": as_of or ""}
    return api("POST", "/api/crash-tests", token=token, json=body)


@mcp.tool()
def get_replay_result(case_id: str = "svb") -> dict:
    """The First Warning Sign Replay: freeze date, outcome, and how each documented warning sign was handled."""
    data = api("GET", f"/api/replay/{case_id}")
    if "error" in data:
        return data
    r = data.get("result") or {}
    return {"company": data["case"]["company"], "freeze_date": data["case"]["freeze_date"], "outcome": data["case"]["outcome"],
            "verdict": r.get("verdict"), "summary": r.get("summary"),
            "signs": [{"id": s["id"], "status": s["status"], "statement": s["statement"]} for s in r.get("signs", [])]}


if __name__ == "__main__":
    run(mcp)