from datetime import date

from app.radar.engine import filing_alerts, load_updates, prioritise, regulatory_alerts, summarise

CO = {"cik": "0000000001", "company": "Test Co"}
FILINGS = [
    {"accession_no": "P22", "form": "DEF 14A", "filing_date": date(2022, 3, 1)},
    {"accession_no": "P23", "form": "PRE 14A", "filing_date": date(2023, 3, 3)},
    {"accession_no": "K23", "form": "10-K", "filing_date": date(2023, 2, 24)},
    {"accession_no": "K24", "form": "10-K", "filing_date": date(2024, 11, 1)},
]


def fake_search(found: dict[str, bool]):
    def search(accessions, pattern):
        acc = accessions[0]
        return [{"accession_no": acc, "form": "X", "page": 7, "text": "matched passage"}] if found.get(acc) else []
    return search


def by_id(alerts):
    return {a["key"].split(":")[1]: a for a in alerts}


def test_updates_file_is_valid():
    ids = [u["id"] for u in load_updates()]
    assert len(ids) == 4 and len(set(ids)) == 4


def test_statuses_and_priorities():
    alerts = by_id(regulatory_alerts(CO, FILINGS, load_updates(), fake_search({"P23": True}), date(2025, 1, 1)))
    assert alerts["sec-2022-pvp"]["evidence"]["status"] == "addressed"          # latest proxy has it
    assert alerts["sec-2022-pvp"]["evidence"]["passage"]["page"] == 7
    assert alerts["sec-2023-cyber"]["evidence"]["status"] == "gap"              # 10-K 2024 lacks it
    assert alerts["sec-2023-cyber"]["priority"] == "high"


def test_rule_not_yet_required_before_applies_from():
    alerts = by_id(regulatory_alerts(CO, FILINGS, load_updates(), fake_search({}), date(2023, 3, 7)))
    assert alerts["sec-2023-cyber"]["evidence"]["status"] == "not_yet_required"
    assert alerts["sec-2023-cyber"]["disclosure_to_review"]["accession_no"] == "K23"   # nothing after as_of
    assert alerts["sec-2023-cyber"]["priority"] == "low"


def test_no_filing_is_insufficient_evidence():
    only_10k = [f for f in FILINGS if f["form"] == "10-K"]
    alerts = by_id(regulatory_alerts(CO, only_10k, load_updates(), fake_search({}), date(2025, 1, 1)))
    assert alerts["sec-2022-pvp"]["evidence"]["status"] == "no_filing"
    assert "Insufficient evidence" in alerts["sec-2022-pvp"]["follow_up"]


def test_filing_stream_and_priority_order():
    refs = [
        {"accession_no": "K24", "form": "10-K", "filing_date": date(2024, 11, 1)},
        {"accession_no": "E25", "form": "8-K", "filing_date": date(2025, 2, 1)},
        {"accession_no": "Q25", "form": "10-Q", "filing_date": date(2025, 5, 1)},
    ]
    new = filing_alerts(CO, {"K24"}, refs)
    assert [a["key"] for a in new] == ["filing:E25"]        # known and unwatched forms skipped
    assert new[0]["priority"] == "high"
    regs = regulatory_alerts(CO, FILINGS, load_updates(), fake_search({"P23": True}), date(2025, 1, 1))
    ordered = prioritise(regs + new)
    assert [a["priority"] for a in ordered] == sorted([a["priority"] for a in ordered],
                                                      key=["high", "medium", "low"].index)
    s = summarise(ordered)
    assert s["by_stream"] == {"regulatory": 4, "filing": 1}

def test_any_applicable_form_can_address_the_rule():
    # clawback looks at the latest 10-K and the latest proxy; the proxy alone is enough
    filings = FILINGS + [{"accession_no": "P25", "form": "DEF 14A", "filing_date": date(2025, 1, 10)}]
    alerts = by_id(regulatory_alerts(CO, filings, load_updates(), fake_search({"P25": True}), date(2025, 6, 1)))
    assert alerts["sec-2022-clawback"]["evidence"]["status"] == "addressed"
    assert alerts["sec-2022-clawback"]["disclosure_to_review"]["accession_no"] == "P25"


def test_quote_is_centred_on_the_match():
    from app.radar.engine import _quote
    text = "x " * 300 + "our compensation recovery policy applies" + " y" * 300
    q = _quote(text, "compensation recovery")
    assert "compensation recovery" in q and q.startswith("...") and len(q) < 400