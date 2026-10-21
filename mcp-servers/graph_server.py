"""nirikkha-graph: the verified relationship graph (Neo4j) of directors, officers, committees and outside bodies."""
from mcp.server.fastmcp import FastMCP

from common import api, run

mcp = FastMCP("nirikkha-graph", port=8103)


def _graph(cik: str, accession: str | None = None) -> dict:
    q = f"?accession={accession}" if accession else ""
    return api("GET", f"/api/graph/{str(cik).strip()}{q}")


@mcp.tool()
def get_relationship_graph(cik: str, accession: str | None = None) -> dict:
    """Counts and people of a company's governance graph from its latest (or a given) proxy statement."""
    g = _graph(cik, accession)
    if "error" in g:
        return g
    people = [{"name": n["label"], "roles": n["roles"], "title": n.get("title")} for n in g["nodes"] if n["kind"] == "person"]
    committees = [n["label"] for n in g["nodes"] if n["kind"] == "committee"]
    return {"company": g["company"], "proxy": g["accession"], "available_proxies": g["accessions"],
            "counts": g["counts"], "people": people, "committees": committees}


@mcp.tool()
def find_interlocks(cik: str, accession: str | None = None) -> list[dict]:
    """Outside organizations shared by two or more of the company's people (conflict-of-interest questions, not findings)."""
    g = _graph(cik, accession)
    if "error" in g:
        return [g]
    by_id = {n["id"]: n for n in g["nodes"]}
    out = []
    for n in g["nodes"]:
        if n["kind"] == "organization" and n.get("shared", 0) >= 2:
            links = [e for e in g["edges"] if e["target"] == n["id"]]
            out.append({"organization": n["label"],
                        "people": [{"name": by_id[e["source"]]["label"], "relation": e["type"], "page": e.get("page"),
                                    "quote": e.get("quote")} for e in links if e["source"] in by_id]})
    return out or [{"note": "No shared outside organizations in this proxy. Try another proxy with get_relationship_graph."}]


@mcp.tool()
def person_connections(cik: str, name: str) -> dict:
    """Every role, committee seat and outside position of one person, each with the page and quote it comes from."""
    g = _graph(cik)
    if "error" in g:
        return g
    match = [n for n in g["nodes"] if n["kind"] == "person" and name.lower() in n["label"].lower()]
    if not match:
        return {"error": f"No person matching '{name}' in this graph."}
    p = match[0]
    by_id = {n["id"]: n for n in g["nodes"]}
    links = [{"relation": e["type"], "with": by_id.get(e["target"] if e["source"] == p["id"] else e["source"], {}).get("label"),
              "page": e.get("page"), "quote": e.get("quote")}
             for e in g["edges"] if p["id"] in (e["source"], e["target"])]
    return {"person": p["label"], "roles": p["roles"], "title": p.get("title"), "connections": links}


if __name__ == "__main__":
    run(mcp)