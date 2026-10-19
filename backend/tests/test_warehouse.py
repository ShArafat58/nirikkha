"""Tests for the DuckDB warehouse using two synthetic 10-K filings."""

from datetime import date

import duckdb

from app.analytics.warehouse import build, section_yoy, term_pattern, term_trend
from app.ingest.parse import Paragraph, ParsedDocument, Section


def make_doc(accession, filed, risk_text, market_text):
    return ParsedDocument(
        cik="0000000001", company="Example Bank", form="10-K", accession_no=accession,
        filing_date=filed, report_date=date(filed.year - 1, 12, 31), url="https://example.invalid",
        has_page_markers=True, page_count=10,
        sections=[
            Section(key="item_1a", title="Item 1A. Risk Factors", page_start=2, page_end=3,
                    paragraphs=[Paragraph(index=0, page=2, text=risk_text)]),
            Section(key="item_7a", title="Item 7A. Market Risk", page_start=5, page_end=5,
                    paragraphs=[Paragraph(index=1, page=5, text=market_text)]),
        ],
    )


def setup_warehouse(tmp_path):
    parsed = tmp_path / "parsed"
    parsed.mkdir()
    docs = [
        make_doc("a-2022", date(2022, 3, 1), "Unrealized losses are possible. " * 10, "Interest rate risk. " * 100),
        make_doc("a-2023", date(2023, 2, 24), "Unrealized losses increased. Unrealized-loss risk. " * 10, "Interest rate risk. " * 50),
    ]
    for d in docs:
        (parsed / f"{d.accession_no}.json").write_text(d.model_dump_json(), encoding="utf-8")
    counts = build(tmp_path)
    return counts, duckdb.connect(str(tmp_path / "analytics.duckdb"), read_only=True)


def test_build_counts(tmp_path):
    counts, con = setup_warehouse(tmp_path)
    assert counts == {"filings": 2, "sections": 4, "paragraphs": 4}
    con.close()


def test_section_yoy_detects_shrinking_section(tmp_path):
    _, con = setup_warehouse(tmp_path)
    rows = {r["section_key"]: r for r in section_yoy(con, "1") if r["prev_chars"]}
    assert rows["item_7a"]["change_pct"] == -50.0
    assert rows["item_1a"]["change_pct"] > 0
    con.close()


def test_term_trend_counts_variants(tmp_path):
    _, con = setup_warehouse(tmp_path)
    trend = term_trend(con, "1", ["unrealized loss"])["unrealized loss"]
    assert [r["hits"] for r in trend] == [10, 20]
    con.close()


def test_term_pattern_treats_space_and_hyphen_alike():
    assert term_pattern("held-to-maturity") == term_pattern("held to maturity")