"""Tests for the Governance Rule Engine using SVB-like synthetic facts (no database, no LLM)."""

from datetime import date

from app.rules.engine import RULES, Facts, Passage, evaluate, parse_amount

PROXY = "0001193125-22-064940"


def row(kind, name, key, org="SVB FINANCIAL GROUP", chair=False, title=None, amount=None, quote="q", from_table=False):
    return {"kind": kind, "person_key": key, "person_name": name, "org_key": org.lower(), "org_name": org, "chair": chair,
            "props": {"accession_no": PROXY, "chunk_id": "c", "page": 10, "section": "S", "quote": quote,
                      "title": title, "independent": None, "amount": amount, "from_table": from_table}}


def passage(key_text):
    return Passage(accession_no=PROXY, form="DEF 14A", filing_date="2022-03-04", section="S", page=17, chunk_id="c",
                   text=key_text)


def svb_facts(**overrides):
    base = dict(
        company="SVB FINANCIAL GROUP", cik="0000719739", as_of=date(2023, 3, 10),
        filings=[{"accession_no": "k22", "form": "10-K", "filing_date": date(2022, 3, 1)},
                 {"accession_no": "k23", "form": "10-K", "filing_date": date(2023, 2, 24)},
                 {"accession_no": PROXY, "form": "DEF 14A", "filing_date": date(2022, 3, 4)}],
        sections={PROXY: {"summary_compensation_table", "related_person_transactions"}},
        relations=[
            row("DIRECTOR_OF", "Roger Dunbar", "roger dunbar"),
            row("DIRECTOR_OF", "Mary Miller", "mary miller"),
            row("DIRECTOR_OF", "Kate Mitchell", "kate mitchell"),
            row("OFFICER_OF", "Greg Becker", "greg becker", title="President and CEO"),
            row("OFFICER_OF", "Laura Izurieta", "laura izurieta", title="Chief Risk Officer"),
            row("BOARD_SEAT", "Greg Becker", "greg becker", org="Federal Reserve Bank of San Francisco"),
            row("MEMBER_OF", "Kate Mitchell", "kate mitchell", org="Risk Committee", chair=True, from_table=True),
            row("MEMBER_OF", "Eric Benhamou", "eric benhamou", org="Audit Committee", chair=True),
            row("MEMBER_OF", "Mary Miller", "mary miller", org="Audit Committee", chair=True),
            row("RELATED_TRANSACTION", "BlackRock, Inc", "blackrock", amount="$30.0 million"),
            row("RELATED_TRANSACTION", "Cachematrix", "cachematrix", amount="$706,674"),
            row("RELATED_TRANSACTION", "Small Vendor", "small vendor", amount="$50,000"),
        ],
        relations_source=PROXY,
        passages={
            "independence": [passage("The Board has determined that each director other than Mr. Becker is independent.")],
            "rpt_policy": [passage("Our policy on related party transactions governs transactions with related persons.")],
            "risk_oversight": [passage("The Board oversees enterprise-wide risk through its Risk Committee.")],
        },
        yoy=[{"section_key": "item_7a", "title": "Item 7A. Market Risk", "filing_date": date(2023, 2, 24),
              "chars": 7957, "prev_chars": 14505, "change_pct": -45.1},
             {"section_key": "item_1a", "title": "Item 1A. Risk Factors", "filing_date": date(2023, 2, 24),
              "chars": 123544, "prev_chars": 119684, "change_pct": 3.2}],
    )
    base.update(overrides)
    return Facts(**base)


def by_id(report):
    return {r["rule_id"]: r for r in report["results"]}


def test_svb_like_results():
    report = evaluate(svb_facts())
    r = by_id(report)
    assert r["R401_DIRECTORS"]["result"] == "PASS"
    assert r["R402_SCT"]["result"] == "PASS"
    assert r["R404_POLICY"]["result"] == "PASS"
    assert r["R407_INDEPENDENCE"]["result"] == "PASS"
    assert r["R407_FIN_EXPERT"]["result"] == "POTENTIAL_GAP"
    assert r["R407_RISK_OVERSIGHT"]["result"] == "PASS"
    assert r["BP_CRO"]["result"] == "PASS"
    assert r["II_DISCLOSURE_FRESHNESS"]["result"] == "PASS"
    assert r["II_YOY_CHANGE"]["result"] == "POTENTIAL_GAP" and "Item 7A" in r["II_YOY_CHANGE"]["rationale"]
    assert r["II_OFFICER_OUTSIDE_ROLES"]["result"] == "POTENTIAL_GAP"
    assert "Federal Reserve Bank of San Francisco" in r["II_OFFICER_OUTSIDE_ROLES"]["rationale"]
    assert r["II_COMMITTEE_CHAIR_CONSISTENCY"]["result"] == "POTENTIAL_GAP"


def test_pvp_not_applicable_before_compliance_date():
    report = evaluate(svb_facts())
    na = {n["rule_id"]: n for n in report["not_applicable"]}
    assert "R402_PVP" in na and "2022-12-16" in na["R402_PVP"]["reason"]


def test_related_person_threshold_and_review():
    r = by_id(evaluate(svb_facts()))["R404_TRANSACTIONS"]
    assert r["result"] == "PASS" and r["human_review"] is True
    assert "2 at or above $120,000" in r["rationale"]


def test_missing_extraction_gives_insufficient_evidence():
    r = by_id(evaluate(svb_facts(relations=[], relations_source=None)))
    for rule_id in ("R401_DIRECTORS", "R404_TRANSACTIONS", "BP_CRO", "II_OFFICER_OUTSIDE_ROLES"):
        assert r[rule_id]["result"] == "INSUFFICIENT_EVIDENCE"


def test_stale_proxy_is_flagged():
    r = by_id(evaluate(svb_facts(as_of=date(2023, 9, 30))))["II_DISCLOSURE_FRESHNESS"]
    assert r["result"] == "POTENTIAL_GAP"


def test_table_evidence_lowers_confidence():
    r = by_id(evaluate(svb_facts()))["BP_RISK_COMMITTEE"]
    assert r["result"] == "PASS" and r["confidence"] == "medium" and r["human_review"] is True


def test_categories_never_mixed_and_summary_adds_up():
    report = evaluate(svb_facts())
    assert {r["category"] for r in report["results"]} <= {"law", "best_practice", "internal_indicator"}
    assert sum(report["summary"]["by_result"].values()) + report["summary"]["not_applicable"] == len(RULES)


def test_parse_amount():
    assert parse_amount("$30.0 million") == 30_000_000
    assert parse_amount("approximately $706,674") == 706_674
    assert parse_amount("none") is None

def test_sentence_snippet_starts_at_matching_sentence():
    from app.rules.engine import RULE_PATTERNS, sentence_snippet

    text = ("Our directors have wine industry experience. The Board has determined that all directors other than "
            "Mr. Becker are independent. Committee members are listed below.")
    quote = sentence_snippet(text, RULE_PATTERNS["independence"])
    assert quote.startswith("The Board has determined")
    assert "wine" not in quote
    assert sentence_snippet(text, r"audit committee financial expert") is None


def test_pattern_must_match_within_one_sentence():
    facts = svb_facts(passages={"independence": [passage("We determined the budget. Directors are independent thinkers.")]})
    r = by_id(evaluate(facts))["R407_INDEPENDENCE"]
    assert r["result"] == "INSUFFICIENT_EVIDENCE"
