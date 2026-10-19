"""Tests for the filing parser using small synthetic filings."""

from datetime import date

from app.ingest.edgar import FilingRef
from app.ingest.parse import parse_filing

TEN_K_HTML = """<html><body>
<div style="display:none"><ix:header><ix:hidden>HIDDEN FACT</ix:hidden></ix:header></div>
<div style="display: none">hidden div</div>
<table><tr><td>Item 1A.</td><td>Risk Factors</td><td>12</td></tr></table>
<hr style="page-break-after:always"/>
<p><b>Item 1.</b> Business</p>
<p>We make <span>widgets</span>
   and sell them worldwide.</p>
<div style="page-break-before: always"></div>
<p>ITEM 1A. RISK FACTORS</p>
<p>Our deposits are concentrated.</p>
<p>Interest rate risk could hurt us.</p>
</body></html>"""

TEN_K_TOC_LINES_HTML = """<html><body>
<p>Table of Contents</p>
<p>Item 1A. Risk Factors</p>
<p>Item 7. MD&amp;A</p>
<p>Forward-looking statements are uncertain.</p>
<hr style="page-break-after:always"/>
<p>Item 1A. Risk Factors</p>
<p>Rates may rise.</p>
<p>Item 7. Management's Discussion</p>
<p>Deposits fell.</p>
</body></html>"""

PROXY_HTML = """<html><body>
<table><tr><td>Corporate Governance</td><td>15</td></tr></table>
<p>CORPORATE GOVERNANCE</p>
<p>Our board has 10 directors, 9 of whom are independent.</p>
<p>Director Independence</p>
<p>The board determined that all directors except the CEO are independent.</p>
<p>Certain Relationships and Related Person Transactions</p>
<p>In 2022, we paid $250,000 to a firm owned by a director&#8217;s spouse.</p>
</body></html>"""

BIG = "Our directors are independent and meet regularly. " * 30

PROXY_TOC_HTML = f"""<html><body>
<p>Corporate Governance</p>
<p>Executive Compensation</p>
<p>CORPORATE GOVERNANCE</p>
<p>{BIG}</p>
<p>Executive Compensation</p>
<p>Pay is linked to performance.</p>
</body></html>"""


def make_ref(form: str) -> FilingRef:
    return FilingRef(
        cik="0000000001",
        company="Example Corp",
        form=form,
        accession_no="0000000001-24-000001",
        filing_date=date(2024, 2, 20),
        report_date=None,
        primary_document="x.htm",
        url="https://example.invalid/x.htm",
    )


def all_text(doc) -> str:
    return " ".join(p.text for s in doc.sections for p in s.paragraphs)


def test_10k_sections_pages_and_cleaning():
    doc = parse_filing(TEN_K_HTML, make_ref("10-K"))
    assert [s.key for s in doc.sections] == ["front_matter", "item_1", "item_1a"]
    assert doc.has_page_markers is True
    assert doc.page_count == 3

    item1 = doc.sections[1]
    assert item1.title == "Item 1. Business"
    assert item1.paragraphs[0].text == "We make widgets and sell them worldwide."
    assert item1.paragraphs[0].page == 2

    item1a = doc.sections[2]
    assert item1a.title == "Item 1A. Risk Factors"
    assert [p.page for p in item1a.paragraphs] == [3, 3]


def test_hidden_xbrl_and_hidden_divs_removed():
    text = all_text(parse_filing(TEN_K_HTML, make_ref("10-K")))
    assert "HIDDEN FACT" not in text
    assert "hidden div" not in text


def test_table_of_contents_row_is_not_a_heading():
    doc = parse_filing(TEN_K_HTML, make_ref("10-K"))
    front = [p.text for p in doc.sections[0].paragraphs]
    assert "Item 1A. | Risk Factors | 12" in front


def test_10k_toc_lines_fold_into_front_matter():
    doc = parse_filing(TEN_K_TOC_LINES_HTML, make_ref("10-K"))
    assert [s.key for s in doc.sections] == ["front_matter", "item_1a", "item_7"]
    assert doc.sections[1].paragraphs[0].text == "Rates may rise."
    assert doc.sections[1].paragraphs[0].page == 2
    front = [p.text for p in doc.sections[0].paragraphs]
    assert "Item 7. MD&A" in front
    assert "Forward-looking statements are uncertain." in front


def test_proxy_sections_without_page_markers():
    doc = parse_filing(PROXY_HTML, make_ref("DEF 14A"))
    assert [s.key for s in doc.sections] == [
        "front_matter",
        "corporate_governance",
        "director_independence",
        "related_person_transactions",
    ]
    assert doc.has_page_markers is False
    assert doc.page_count is None
    assert all(p.page is None for s in doc.sections for p in s.paragraphs)
    assert "$250,000" in doc.sections[3].paragraphs[0].text


def test_proxy_toc_entries_fold_into_front_matter():
    doc = parse_filing(PROXY_TOC_HTML, make_ref("DEF 14A"))
    assert [s.key for s in doc.sections] == ["front_matter", "corporate_governance", "executive_compensation"]
    front = [p.text for p in doc.sections[0].paragraphs]
    assert front == ["Corporate Governance", "Executive Compensation"]
    assert doc.sections[2].paragraphs[0].text == "Pay is linked to performance."