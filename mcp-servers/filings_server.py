"""nirikkha-filings: which companies Nirikkha has loaded, and what a company has filed on SEC EDGAR."""
import httpx
from mcp.server.fastmcp import FastMCP

from common import UA, api, run

mcp = FastMCP("nirikkha-filings", port=8101)
FORMS = {"10-K", "DEF 14A", "PRE 14A", "8-K", "10-Q"}


@mcp.tool()
def list_companies() -> list[dict]:
    """Companies whose filings are loaded in Nirikkha, with filing and chunk counts."""
    data = api("GET", "/api/companies")
    if isinstance(data, dict) and "error" in data:
        return [data]
    return [{"cik": c.get("cik"), "company": c.get("company"), "filings": c.get("filing_count"),
             "chunks": c.get("chunk_count")} for c in data]


@mcp.tool()
def list_sec_filings(cik: str, limit: int = 10) -> list[dict]:
    """Most recent governance-relevant filings (10-K, proxy, 8-K, 10-Q) of a company on SEC EDGAR.

    cik: SEC Central Index Key, digits only (e.g. 320193 for Apple).
    """
    url = f"https://data.sec.gov/submissions/CIK{str(cik).strip().zfill(10)}.json"
    try:
        r = httpx.get(url, headers={"User-Agent": UA}, timeout=30)
        r.raise_for_status()
    except httpx.HTTPError as exc:
        return [{"error": f"SEC EDGAR request failed: {exc}"}]
    rec = r.json().get("filings", {}).get("recent", {})
    out = []
    for form, date, acc, doc in zip(rec.get("form", []), rec.get("filingDate", []),
                                    rec.get("accessionNumber", []), rec.get("primaryDocument", [])):
        if form in FORMS:
            path = acc.replace("-", "")
            out.append({"form": form, "filing_date": date, "accession_no": acc,
                        "url": f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{path}/{doc}"})
        if len(out) >= max(1, min(limit, 40)):
            break
    return out


if __name__ == "__main__":
    run(mcp)