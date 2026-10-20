"""Load resolved governance relations into Neo4j and answer graph questions.

Graph model:
  (:Company {cik, name})-[:FILED]->(:Filing {accession_no, form, filing_date})
  (:Person)-[:DIRECTOR_OF | OFFICER_OF | CHAIRS_BOARD]->(:Company)
  (:Person)-[:MEMBER_OF {chair}]->(:Committee)-[:COMMITTEE_OF]->(:Company)
  (:Person)-[:BOARD_SEAT | EMPLOYED_BY]->(:Organization)
  (:Party)-[:RELATED_TRANSACTION {amount}]->(:Company)
Every relationship carries its evidence: accession_no, chunk_id, page, section, quote.
Reloading a filing first deletes that filing's relationships (idempotent).

Run directly:
    python -m app.graph.store --load 0001193125-22-064940
    python -m app.graph.store --report 719739
"""

from __future__ import annotations

import argparse
import json
import sys

from neo4j import GraphDatabase
from neo4j.exceptions import Neo4jError, ServiceUnavailable

from app.config import get_settings
from app.graph.resolve import build_rows
from app.ingest.edgar import normalize_cik


class GraphError(RuntimeError):
    """Raised with a clear message when Neo4j is not reachable or misconfigured."""


CYPHER = {
    "DIRECTOR_OF": """
        UNWIND $rows AS r MATCH (c:Company {cik: $cik})
        MERGE (p:Person {key: r.person_key}) SET p.name = r.person_name
        MERGE (p)-[x:DIRECTOR_OF {accession_no: r.props.accession_no}]->(c) SET x += r.props""",
    "OFFICER_OF": """
        UNWIND $rows AS r MATCH (c:Company {cik: $cik})
        MERGE (p:Person {key: r.person_key}) SET p.name = r.person_name
        MERGE (p)-[x:OFFICER_OF {accession_no: r.props.accession_no}]->(c) SET x += r.props""",
    "CHAIRS_BOARD": """
        UNWIND $rows AS r MATCH (c:Company {cik: $cik})
        MERGE (p:Person {key: r.person_key}) SET p.name = r.person_name
        MERGE (p)-[x:CHAIRS_BOARD {accession_no: r.props.accession_no}]->(c) SET x += r.props""",
    "MEMBER_OF": """
        UNWIND $rows AS r MATCH (c:Company {cik: $cik})
        MERGE (p:Person {key: r.person_key}) SET p.name = r.person_name
        MERGE (k:Committee {key: r.org_key}) SET k.name = r.org_name
        MERGE (k)-[:COMMITTEE_OF]->(c)
        MERGE (p)-[x:MEMBER_OF {accession_no: r.props.accession_no}]->(k)
        SET x += r.props, x.chair = coalesce(x.chair, false) OR r.chair""",
    "BOARD_SEAT": """
        UNWIND $rows AS r
        MERGE (p:Person {key: r.person_key}) SET p.name = r.person_name
        MERGE (o:Organization {key: r.org_key}) SET o.name = r.org_name
        MERGE (p)-[x:BOARD_SEAT {accession_no: r.props.accession_no}]->(o) SET x += r.props""",
    "EMPLOYED_BY": """
        UNWIND $rows AS r
        MERGE (p:Person {key: r.person_key}) SET p.name = r.person_name
        MERGE (o:Organization {key: r.org_key}) SET o.name = r.org_name
        MERGE (p)-[x:EMPLOYED_BY {accession_no: r.props.accession_no}]->(o) SET x += r.props""",
    "RELATED_TRANSACTION": """
        UNWIND $rows AS r MATCH (c:Company {cik: $cik})
        MERGE (e:Party {key: r.person_key}) SET e.name = r.person_name
        MERGE (e)-[x:RELATED_TRANSACTION {accession_no: r.props.accession_no, chunk_id: r.props.chunk_id}]->(c)
        SET x += r.props""",
}

REPORT_QUERIES = {
    "Board (directors, outside seats)": """
        MATCH (p:Person)-[:DIRECTOR_OF]->(c:Company {cik: $cik})
        OPTIONAL MATCH (p)-[:BOARD_SEAT]->(o:Organization)
        RETURN p.name AS director, count(DISTINCT o) AS outside_seats
        ORDER BY outside_seats DESC, director""",
    "Board chair": """
        MATCH (p:Person)-[x:CHAIRS_BOARD]->(c:Company {cik: $cik})
        RETURN DISTINCT p.name AS chair, x.page AS page""",
    "Committees": """
        MATCH (p:Person)-[m:MEMBER_OF]->(k:Committee)-[:COMMITTEE_OF]->(c:Company {cik: $cik})
        RETURN k.name AS committee,
               collect(DISTINCT CASE WHEN m.chair THEN p.name + ' (chair)' ELSE p.name END) AS members
        ORDER BY committee""",
    "Executive officers with outside roles": """
        MATCH (p:Person)-[:OFFICER_OF]->(c:Company {cik: $cik})
        MATCH (p)-[x:BOARD_SEAT|EMPLOYED_BY]->(o:Organization)
        RETURN p.name AS officer, type(x) AS role, o.name AS organization, x.page AS page
        ORDER BY officer, organization""",
    "Shared outside organizations (interlocks)": """
        MATCH (p1:Person)-[:DIRECTOR_OF|OFFICER_OF]->(c:Company {cik: $cik})<-[:DIRECTOR_OF|OFFICER_OF]-(p2:Person)
        WHERE p1.key < p2.key
        MATCH (p1)-[:BOARD_SEAT|EMPLOYED_BY]->(o:Organization)<-[:BOARD_SEAT|EMPLOYED_BY]-(p2)
        RETURN o.name AS organization, p1.name AS person_1, p2.name AS person_2""",
    "Related-party transactions": """
        MATCH (e:Party)-[x:RELATED_TRANSACTION]->(c:Company {cik: $cik})
        RETURN e.name AS party, x.amount AS amount, x.page AS page, x.quote AS quote""",
}


def get_driver():
    s = get_settings()
    if not (s.neo4j_uri and s.neo4j_username and s.neo4j_password):
        raise GraphError("NEO4J_URI / NEO4J_USERNAME / NEO4J_PASSWORD are not set in backend/.env.")
    driver = GraphDatabase.driver(s.neo4j_uri, auth=(s.neo4j_username, s.neo4j_password), notifications_min_severity="OFF")
    try:
        driver.verify_connectivity()
    except (ServiceUnavailable, Neo4jError) as exc:
        driver.close()
        raise GraphError(f"Could not connect to Neo4j: {exc.__class__.__name__}. Is the Aura instance running (not paused)?") from exc
    return driver


def _database() -> str | None:
    return get_settings().neo4j_database or None


def ensure_constraints(driver) -> None:
    with driver.session(database=_database()) as session:
        for label in ("Person", "Organization", "Committee", "Party"):
            session.run(f"CREATE CONSTRAINT {label.lower()}_key IF NOT EXISTS FOR (n:{label}) REQUIRE n.key IS UNIQUE")
        session.run("CREATE CONSTRAINT company_cik IF NOT EXISTS FOR (n:Company) REQUIRE n.cik IS UNIQUE")
        session.run("CREATE CONSTRAINT filing_acc IF NOT EXISTS FOR (n:Filing) REQUIRE n.accession_no IS UNIQUE")


def load_extracted(driver, extracted: dict) -> dict:
    rows = build_rows(extracted)
    counts: dict[str, int] = {}
    with driver.session(database=_database()) as session:
        session.run(
            "MERGE (c:Company {cik: $cik}) SET c.name = $company "
            "MERGE (f:Filing {accession_no: $acc}) SET f.form = $form, f.filing_date = date($filed) "
            "MERGE (c)-[:FILED]->(f)",
            cik=extracted["cik"], company=extracted["company"], acc=extracted["accession_no"],
            form=extracted["form"], filed=extracted["filing_date"],
        )
        session.run("MATCH ()-[x]->() WHERE x.accession_no = $acc DELETE x", acc=extracted["accession_no"])
        for kind, cypher in CYPHER.items():
            batch = [r for r in rows if r["kind"] == kind]
            if batch:
                session.run(cypher, rows=batch, cik=extracted["cik"])
                counts[kind] = len(batch)
    return counts


def report(driver, cik: str) -> dict[str, list[dict]]:
    out: dict[str, list[dict]] = {}
    with driver.session(database=_database()) as session:
        for title, query in REPORT_QUERIES.items():
            out[title] = [dict(record) for record in session.run(query, cik=normalize_cik(cik))]
    return out


def _main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Neo4j governance graph")
    parser.add_argument("--load", metavar="ACCESSION_NO")
    parser.add_argument("--report", metavar="CIK")
    args = parser.parse_args(argv[1:])

    try:
        driver = get_driver()
    except GraphError as exc:
        print(f"ERROR: {exc}")
        return 1
    try:
        if args.load:
            path = get_settings().cache_dir / "extracted" / f"{args.load}.json"
            if not path.exists():
                print(f"ERROR: {path.name} not found. Run: python -m app.graph.extract {args.load}")
                return 1
            ensure_constraints(driver)
            counts = load_extracted(driver, json.loads(path.read_text(encoding="utf-8")))
            print(f"Loaded {args.load}: {counts}")
        if args.report:
            for title, rows in report(driver, args.report).items():
                print(f"\n== {title} ({len(rows)}) ==")
                for row in rows[:20]:
                    print("  " + " | ".join(f"{k}: {v}" for k, v in row.items()))
    finally:
        driver.close()
    return 0


if __name__ == "__main__":
    sys.exit(_main(sys.argv))