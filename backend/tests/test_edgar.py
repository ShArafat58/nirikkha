"""Offline tests for the EDGAR client (fake SEC responses, no network)."""

from datetime import date

import httpx
import pytest

from app.ingest.edgar import EdgarClient, EdgarError, normalize_cik

UA = "Nirikkha Test test@nirikkha.dev"

SUBMISSIONS = {
    "name": "Example Corp",
    "filings": {
        "recent": {
            "form": ["10-K", "8-K", "DEF 14A", "10-K", "DEF 14A", "10-K/A"],
            "accessionNumber": [
                "0000000001-24-000001",
                "0000000001-24-000002",
                "0000000001-24-000003",
                "0000000001-23-000004",
                "0000000001-23-000005",
                "0000000001-24-000006",
            ],
            "filingDate": ["2024-02-20", "2024-03-01", "2024-03-10", "2023-02-21", "2023-03-11", "2024-04-01"],
            "reportDate": ["2023-12-31", "", "", "2022-12-31", "", ""],
            "primaryDocument": [
                "ex-20231231.htm",
                "8k.htm",
                "def14a2024.htm",
                "ex-20221231.htm",
                "def14a2023.htm",
                "10ka.htm",
            ],
        },
        "files": [],
    },
}

TICKERS = {"0": {"cik_str": 1, "ticker": "EXM", "title": "Example Corp"}}


def make_client(seen: list) -> EdgarClient:
    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        url = str(request.url)
        if url.endswith("company_tickers.json"):
            return httpx.Response(200, json=TICKERS)
        if "submissions/CIK0000000001.json" in url:
            return httpx.Response(200, json=SUBMISSIONS)
        if url.endswith(".htm"):
            return httpx.Response(200, text="<html><body>Item 1A. Risk Factors</body></html>")
        return httpx.Response(404)

    return EdgarClient(UA, cache_dir=None, min_interval=0, transport=httpx.MockTransport(handler))


def test_normalize_cik():
    assert normalize_cik("719739") == "0000719739"
    assert normalize_cik(1) == "0000000001"


def test_rejects_missing_user_agent():
    with pytest.raises(EdgarError):
        EdgarClient("", cache_dir=None)


def test_rejects_placeholder_user_agent():
    with pytest.raises(EdgarError):
        EdgarClient("Nirikkha Your Name your-email@example.com", cache_dir=None)


def test_lookup_by_ticker_sends_user_agent():
    seen: list = []
    client = make_client(seen)
    cik, name = client.lookup_company("exm")
    assert cik == "0000000001"
    assert name == "Example Corp"
    assert seen[0].headers["User-Agent"] == UA


def test_list_filings_keeps_only_10k_and_proxy_newest_first():
    client = make_client([])
    refs = client.list_filings("1")
    assert [(r.form, r.filing_date) for r in refs] == [
        ("DEF 14A", date(2024, 3, 10)),
        ("10-K", date(2024, 2, 20)),
        ("DEF 14A", date(2023, 3, 11)),
        ("10-K", date(2023, 2, 21)),
    ]
    assert refs[1].url == "https://www.sec.gov/Archives/edgar/data/1/000000000124000001/ex-20231231.htm"


def test_before_cutoff_freezes_evidence():
    client = make_client([])
    refs = client.list_filings("1", before=date(2024, 3, 1))
    assert all(r.filing_date < date(2024, 3, 1) for r in refs)
    assert [r.accession_no for r in refs] == [
        "0000000001-24-000001",
        "0000000001-23-000005",
        "0000000001-23-000004",
    ]


def test_fetch_document_returns_text():
    client = make_client([])
    ref = client.list_filings("1")[1]
    assert "Risk Factors" in client.fetch_document(ref)


def test_unknown_ticker_gives_clear_error():
    client = make_client([])
    with pytest.raises(EdgarError, match="Ticker not found"):
        client.lookup_company("NOPE")