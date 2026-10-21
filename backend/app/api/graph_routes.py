"""Relationship graph API: directors, officers, committees, outside organizations and
related parties of one company, read from Neo4j. Everything comes from public filings.

GET /api/graph/{cik}?accession=...   (default: the latest proxy that was extracted)
"""
from __future__ import annotations

import re
from typing import Any, Callable

from fastapi import APIRouter, Depends, HTTPException

router = APIRouter(prefix="/api/graph", tags=["relationship graph"])
GraphReader = Callable[[str, "str | None"], dict]

Q_ACCESSIONS = """MATCH (:Person)-[r:DIRECTOR_OF|OFFICER_OF]->(:Company {cik: $cik})
RETURN DISTINCT r.accession_no AS acc"""
Q_ROLES = """MATCH (p:Person)-[r:DIRECTOR_OF|OFFICER_OF|CHAIRS_BOARD]->(c:Company {cik: $cik})
WHERE r.accession_no = $acc
RETURN c.name AS company, p.key AS pk, p.name AS pn, type(r) AS rel, r.title AS title, r.page AS page, r.quote AS quote"""
Q_COMMITTEES = """MATCH (p:Person)-[m:MEMBER_OF]->(k:Committee)-[:COMMITTEE_OF]->(:Company {cik: $cik})
WHERE m.accession_no = $acc
RETURN p.key AS pk, p.name AS pn, k.key AS kk, k.name AS kn, m.chair AS chair, m.page AS page, m.quote AS quote"""
Q_OUTSIDE = """MATCH (p:Person)-[x:BOARD_SEAT|EMPLOYED_BY]->(o:Organization)
WHERE x.accession_no = $acc
RETURN p.key AS pk, p.name AS pn, o.key AS okey, o.name AS oname, type(x) AS rel, x.page AS page, x.quote AS quote"""
Q_RELATED = """MATCH (e:Party)-[x:RELATED_TRANSACTION]->(:Company {cik: $cik})
WHERE x.accession_no = $acc
RETURN e.key AS ek, e.name AS en, x.amount AS amount, x.page AS page, x.quote AS quote"""

ROLE = {"DIRECTOR_OF": "director", "OFFICER_OF": "officer", "CHAIRS_BOARD": "board_chair"}


def _acc_key(acc: str) -> tuple[int, int]:
    parts = acc.split("-")
    try:
        return int(parts[1]), int(parts[2])
    except (IndexError, ValueError):
        return 0, 0


def build(cik: str, acc: str, accessions: list[str], roles: list[dict], committees: list[dict],
          outside: list[dict], related: list[dict]) -> dict:
    nodes: dict[str, dict] = {}
    edges: dict[tuple[str, str, str], dict] = {}

    def node(nid: str, label: str, kind: str) -> dict:
        return nodes.setdefault(nid, {"id": nid, "label": label, "kind": kind, "roles": []})

    def edge(src: str, dst: str, kind: str, r: dict, **extra: Any) -> None:
        edges.setdefault((src, dst, kind), {"source": src, "target": dst, "type": kind, "page": r.get("page"),
                                            "quote": str(r.get("quote") or "")[:300], **extra})

    company = next((r["company"] for r in roles if r.get("company")), cik)
    cid = f"c:{cik}"
    node(cid, company, "company")
    for r in roles:
        p = node(f"p:{r['pk']}", r["pn"], "person")
        role = ROLE.get(r["rel"], r["rel"].lower())
        if role not in p["roles"]:
            p["roles"].append(role)
        if role == "officer" and r.get("title"):
            p["title"] = r["title"]
        edge(p["id"], cid, role, r)
    for r in committees:
        p = node(f"p:{r['pk']}", r["pn"], "person")
        k = node(f"k:{r['kk']}", r["kn"], "committee")
        edge(k["id"], cid, "committee_of", {})
        edge(p["id"], k["id"], "chair" if r.get("chair") else "member", r)
    people = {n["id"] for n in nodes.values() if n["kind"] == "person"}
    for r in outside:
        pid = f"p:{r['pk']}"
        if pid not in people:
            continue
        o = node(f"o:{r['okey']}", r["oname"], "organization")
        edge(pid, o["id"], "board_seat" if r["rel"] == "BOARD_SEAT" else "employed_by", r)
    for r in related:
        e = node(f"x:{r['ek']}", r["en"], "party")
        edge(e["id"], cid, "related_transaction", r, amount=r.get("amount"))

    linked: dict[str, set[str]] = {}
    for (src, dst, _), _e in edges.items():
        if dst.startswith("o:"):
            linked.setdefault(dst, set()).add(src)
    for oid, who in linked.items():
        nodes[oid]["shared"] = len(who)

    counts: dict[str, int] = {}
    for n in nodes.values():
        counts[n["kind"]] = counts.get(n["kind"], 0) + 1
    counts["interlocks"] = sum(1 for n in nodes.values() if n.get("shared", 0) >= 2)
    return {"cik": cik, "company": company, "accession": acc, "accessions": sorted(accessions, key=_acc_key, reverse=True),
            "nodes": list(nodes.values()), "edges": list(edges.values()), "counts": counts}


def neo4j_reader(cik: str, accession: str | None) -> dict:
    from app.graph.store import get_driver

    with get_driver() as driver, driver.session() as s:
        accs = [r["acc"] for r in s.run(Q_ACCESSIONS, cik=cik).data() if r.get("acc")]
        if not accs:
            return build(cik, "", [], [], [], [], [])
        acc = accession if accession in accs else max(accs, key=_acc_key)
        args = {"cik": cik, "acc": acc}
        return build(cik, acc, accs, s.run(Q_ROLES, **args).data(), s.run(Q_COMMITTEES, **args).data(),
                     s.run(Q_OUTSIDE, **args).data(), s.run(Q_RELATED, **args).data())


def get_graph_reader() -> GraphReader:
    return neo4j_reader


@router.get("/{cik}")
def get_graph(cik: str, accession: str | None = None, reader: GraphReader = Depends(get_graph_reader)) -> dict:
    if not re.fullmatch(r"\d{1,10}", cik):
        raise HTTPException(status_code=404, detail="Unknown company.")
    try:
        data = reader(cik.zfill(10), accession)
    except Exception:
        raise HTTPException(status_code=503, detail="The relationship graph is temporarily unavailable "
                            "(the graph database may be waking up). Please try again in a minute.")
    if len(data["nodes"]) <= 1:
        raise HTTPException(status_code=404, detail="No relationship graph for this company yet.")
    return data