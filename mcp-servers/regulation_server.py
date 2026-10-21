"""nirikkha-regulation: what an SEC disclosure item requires, recent rule changes, and Radar alerts for a company."""
import json

from mcp.server.fastmcp import FastMCP

from common import ROOT, api, run

mcp = FastMCP("nirikkha-regulation", port=8105)

SK = {
    "401": "Directors and executive officers: names, ages, positions, business experience and other public company directorships.",
    "402": "Executive compensation: Summary Compensation Table (402(c)), pay versus performance (402(v)), clawback recovery (402(w)), option-grant timing (402(x)).",
    "404": "Transactions with related persons above $120,000 (404(a)) and the policy for reviewing and approving them (404(b)).",
    "407": "Corporate governance: director independence (407(a)), committees, audit committee financial expert (407(d)(5)), board leadership and risk oversight (407(h)).",
    "106": "Cybersecurity: processes for managing cybersecurity risk, board oversight and management's role (annual report).",
    "408": "Insider trading: directors' and officers' trading plans (408(a)) and insider trading policies (408(b)).",
}


@mcp.tool()
def explain_sk_item(item: str) -> dict:
    """Plain-language summary of an SEC Regulation S-K item (401, 402, 404, 407, 106 or 408). Not legal advice."""
    key = "".join(ch for ch in item if ch.isdigit())[:3]
    if key not in SK:
        return {"error": f"Item {item} is not in Nirikkha's library yet.", "available": sorted(SK)}
    return {"item": f"Regulation S-K Item {key}", "summary": SK[key], "note": "Summary for orientation, not legal advice."}


@mcp.tool()
def list_rule_changes() -> list[dict]:
    """Curated SEC rule changes the Regulatory Change Radar watches, with adoption dates and sources."""
    path = ROOT / "backend" / "data" / "radar" / "regulatory_updates.json"
    try:
        updates = json.loads(path.read_text(encoding="utf-8-sig"))["updates"]
    except Exception as exc:
        return [{"error": f"Rule-change list not readable: {exc}"}]
    return [{"id": u["id"], "title": u["title"], "adopted": u["adopted"], "items": u["items"],
             "what_changed": u["what_changed"], "applies": u["applies"], "sources": u["sources"]} for u in updates]


@mcp.tool()
def get_radar_alerts(cik: str | None = None) -> dict:
    """Prioritised Radar alerts (rule changes and new filings) and their human decision status."""
    q = f"?cik={str(cik).zfill(10)}" if cik else ""
    data = api("GET", f"/api/radar{q}")
    if "error" in data:
        return data
    return {"summary": data["summary"],
            "alerts": [{"company": a["company"], "title": a["title"], "priority": a["priority"], "status": a["status"],
                        "evidence": a["evidence"]["status"], "follow_up": a["follow_up"]} for a in data["alerts"]]}


if __name__ == "__main__":
    run(mcp)