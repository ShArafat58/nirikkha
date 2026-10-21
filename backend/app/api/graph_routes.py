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


NICK = {"tom": "thomas", "tommy": "thomas", "bob": "robert", "rob": "robert", "bill": "william", "will": "william",
        "jim": "james", "mike": "michael", "dan": "daniel", "liz": "elizabeth", "beth": "elizabeth", "kate": "katherine",
        "joe": "joseph", "ron": "ronald", "art": "arthur", "sue": "susan", "chris": "christopher", "steve": "stephen",
        "tim": "timothy", "andy": "andrew", "alex": "alexander", "greg": "gregory", "jeff": "jeffrey", "rick": "richard"}
TITLES = {"mr", "ms", "mrs", "dr", "jr", "sr", "ii", "iii"}
ABBR = [(r"\bcomp\s*/\s*hc\b", "compensation and human capital"), (r"&", " and "), (r"\bhc\b", "human capital")]


def _name_tokens(label: str) -> list[str]:
    base = label.split(",")[0]
    base = re.sub(r'\\?"[^"]*\\?"', " ", base)  # drop quoted nicknames such as "Busy"
    return [t for t in re.findall(r"[a-z]+", base.lower()) if t not in TITLES]


def committee_key(label: str) -> str:
    s = label.lower()
    for pattern, repl in ABBR:
        s = re.sub(pattern, repl, s)
    return " ".join(re.sub(r"[^a-z ]", " ", s).split())


def _merge_people(nodes: dict, edges: dict) -> tuple[dict, dict]:
    people = [n for n in nodes.values() if n["kind"] == "person"]
    weight = {n["id"]: sum(1 for k in edges if n["id"] in k[:2]) for n in people}
    groups: dict[tuple[str, str], list[dict]] = {}
    singles = []
    for n in people:
        toks = _name_tokens(n["label"])
        if len(toks) >= 2:
            groups.setdefault((NICK.get(toks[0], toks[0]), toks[-1]), []).append(n)
        elif toks:
            singles.append((toks[0], n))
    alias: dict[str, str] = {}
    for members in groups.values():
        canon = max(members, key=lambda n: ("," not in n["label"], weight[n["id"]], len(n["label"])))
        for n in members:
            if n["id"] != canon["id"]:
                alias[n["id"]] = canon["id"]
    for last, n in singles:
        cands = {alias.get(m["id"], m["id"]) for key, ms in groups.items() if key[1] == last for m in ms}
        if len(cands) == 1:
            alias[n["id"]] = cands.pop()
    for old, new in alias.items():
        a, b = nodes[old], nodes[new]
        b["roles"] = sorted(set(b["roles"]) | set(a["roles"]), key=["board_chair", "director", "officer"].index
                            if all(r in ("board_chair", "director", "officer") for r in set(b["roles"]) | set(a["roles"])) else str)
        if a.get("title") and not b.get("title"):
            b["title"] = a["title"]
        del nodes[old]
    merged: dict[tuple[str, str, str], dict] = {}
    for (src, dst, kind), e in edges.items():
        src, dst = alias.get(src, src), alias.get(dst, dst)
        if src != dst:
            merged.setdefault((src, dst, kind), {**e, "source": src, "target": dst})
    return nodes, merged


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
        label = str(r["kn"]).strip()
        if label.lower().startswith("the "):  # e.g. "The Bretton Woods Committee": an outside body
            o = node(f"o:{committee_key(label)}", label, "organization")
            edge(p["id"], o["id"], "outside_member", r)
            continue
        k = node(f"k:{cik}:{committee_key(label)}", label, "committee")
        if len(label) > len(k["label"]):
            k["label"] = label
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

    nodes, edges = _merge_people(nodes, edges)

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