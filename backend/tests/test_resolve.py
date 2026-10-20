"""Tests for entity resolution (no database)."""

from app.graph.resolve import build_rows, display_name, is_board_chair, is_filer, org_key, person_key, resolve_people


def test_person_keys_merge_case_titles_and_nicknames():
    assert person_key("MARY MILLER") == person_key("Mary Miller") == "mary miller"
    assert person_key('Elizabeth "Busy" Burr') == person_key("Elizabeth Busy Burr") == "elizabeth burr"
    assert person_key("Beverly Kay Matthews") == "beverly matthews"


def test_bare_surname_attaches_to_unique_full_name():
    mapping = resolve_people(["Elizabeth Busy Burr", "Ms. Burr", "Greg Becker"])
    assert mapping["Ms. Burr"] == "elizabeth burr"


def test_org_keys_ignore_suffixes_and_ampersand():
    assert org_key("Financial Engines, Inc.") == org_key("Financial Engines")
    assert org_key("Compensation & Human Capital Committee") == org_key("Compensation and Human Capital Committee")


def test_filer_and_board_chair_detection():
    assert is_filer("SVB FINANCIAL GROUP", "SVB FINANCIAL GROUP")
    assert not is_filer("Coursera, Inc.", "SVB FINANCIAL GROUP")
    assert is_board_chair("Board Chair") and is_board_chair("Chairman of the Board")
    assert not is_board_chair("Audit Committee")


def test_display_name_prefers_mixed_case():
    assert display_name(["MARY MILLER", "Mary Miller"]) == "Mary Miller"
    assert display_name(["JOEL FRIEDMAN"]) == "Joel Friedman"


def test_build_rows_maps_relations_and_drops_unverified():
    base = {"accession_no": "a", "chunk_id": "c", "page_start": 10, "section_title": "S", "title": None,
            "independent": None, "amount": None, "quote": "q"}
    extracted = {"company": "SVB FINANCIAL GROUP", "cik": "0000719739", "relations": [
        {**base, "person": "GREG BECKER", "relation": "OFFICER_OF", "organization": "SVB FINANCIAL GROUP", "verified": True},
        {**base, "person": "Greg Becker", "relation": "BOARD_SEAT_ELSEWHERE",
         "organization": "Federal Reserve Bank of San Francisco", "verified": True},
        {**base, "person": "Roger Dunbar", "relation": "COMMITTEE_CHAIR", "organization": "Board Chair", "verified": True},
        {**base, "person": "Kate Mitchell", "relation": "COMMITTEE_CHAIR", "organization": "Risk Committee", "verified": True},
        {**base, "person": "Someone", "relation": "DIRECTOR_OF", "organization": "SVB FINANCIAL GROUP", "verified": False},
    ]}
    rows = build_rows(extracted)
    kinds = [(r["kind"], r["person_name"]) for r in rows]
    assert ("OFFICER_OF", "Greg Becker") in kinds
    assert ("BOARD_SEAT", "Greg Becker") in kinds
    assert ("CHAIRS_BOARD", "Roger Dunbar") in kinds
    member = next(r for r in rows if r["kind"] == "MEMBER_OF")
    assert member["chair"] is True and member["org_key"].startswith("0000719739:")
    assert all(r["person_name"] != "Someone" for r in rows)

def test_multi_person_phrases_and_outside_committees():
    from app.graph.resolve import is_multi_person, outside_committee_owner

    assert is_multi_person("Messrs. Daniels and Staglin")
    assert not is_multi_person("Alison Davis")
    assert outside_committee_owner("Investment Committee of Waterman Ventures", "SVB FINANCIAL GROUP") == "Waterman Ventures"
    assert outside_committee_owner("Risk Committee", "SVB FINANCIAL GROUP") is None


def test_table_evidence_is_flagged():
    extracted = {"company": "SVB FINANCIAL GROUP", "cik": "0000719739", "relations": [
        {"person": "Eric Benhamou", "relation": "COMMITTEE_CHAIR", "organization": "Audit Committee",
         "accession_no": "a", "chunk_id": "c", "page_start": 5, "section_title": "S", "title": None,
         "independent": None, "amount": None, "quote": "Eric Benhamou | 66 | 2005 | 2 | X | C", "verified": True},
    ]}
    assert build_rows(extracted)[0]["props"]["from_table"] is True
