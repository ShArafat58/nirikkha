from datetime import date

from app.graph.resolve import build_rows
from app.rules.engine import RULES, Facts, Passage, evaluate

LEADERSHIP = [r for r in RULES if r.id == "II_RISK_LEADERSHIP_CHANGE"]


def _facts(text: str | None) -> Facts:
    f = Facts(company="Co", cik="0000000001", as_of=date(2023, 3, 7),
              filings=[{"accession_no": "P", "form": "PRE 14A", "filing_date": date(2023, 3, 3)}])
    if text is not None:
        f.passages["risk_leadership_change"] = [Passage(
            accession_no="P", form="PRE 14A", filing_date="2023-03-03", section="Executive Officers",
            page=45, chunk_id="c1", text=text, score=1.0)]
    return f


def test_cro_departure_is_flagged_with_its_passage():
    r = evaluate(_facts("Ms. Smith entered into a separation agreement and ceased serving as Chief Risk Officer."),
                 LEADERSHIP)["results"][0]
    assert r["result"] == "POTENTIAL_GAP" and r["human_review"] is True
    assert "Chief Risk Officer" in r["evidence"][0]["quote"] and r["evidence"][0]["page"] == 45


def test_no_change_passes():
    r = evaluate(_facts("Kim Olson, Chief Risk Officer, leads the risk function."), LEADERSHIP)["results"][0]
    assert r["result"] == "PASS"


def _rel(person, org, quote):
    return {"relation": "COMMITTEE_MEMBER", "person": person, "organization": org, "verified": True,
            "accession_no": "A", "chunk_id": "c", "page_start": 10, "section_title": "s", "quote": quote}


def test_table_row_without_committee_name_is_dropped():
    rows = build_rows({"company": "SVB FINANCIAL GROUP", "cik": "0000719739", "relations": [
        _rel("Greg Becker", "Audit Committee", "Greg Becker, CEO & President | 55 | 2011 | X | X |"),
        _rel("Mary Miller", "Risk Committee", "Mary Miller | 66 | 2020 | Risk Committee member |"),
        _rel("John Doe", "Finance Committee", "Mr. Doe serves on the Finance Committee."),
    ]})
    members = {(r["person_name"], r["org_name"]) for r in rows if r["kind"] == "MEMBER_OF"}
    assert ("Greg Becker", "Audit Committee") not in members
    assert ("Mary Miller", "Risk Committee") in members
    assert ("John Doe", "Finance Committee") in members