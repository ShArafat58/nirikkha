"""Parse SEC filing HTML into sections and paragraphs with page numbers.

Page numbers come only from the filer's own page-break markers (CSS
page-break-before/after, break-before/after). If a document has none,
page is None - we never invent page numbers.

Table-of-contents entries are folded into the "front_matter" section:
- 10-K: if an Item heading appears more than once, the LAST occurrence is the real section.
- Proxy: tiny "sections" (< 300 chars) before the first substantial section (>= 1000 chars) are TOC.

Run directly (parses and saves JSON to backend/.cache/parsed/):
    python -m app.ingest.parse 719739 --before 2023-03-10
    python -m app.ingest.parse AAPL
"""

from __future__ import annotations

import re
import sys
import time
import warnings
from datetime import date

from bs4 import BeautifulSoup, Comment, NavigableString, XMLParsedAsHTMLWarning
from pydantic import BaseModel

from app.ingest.edgar import EdgarClient, EdgarError, FilingRef

# EDGAR filings are XHTML (inline XBRL); the HTML parser handles them correctly.
warnings.filterwarnings("ignore", category=XMLParsedAsHTMLWarning)

PAGE_MARK = "@@NIRIKKHA_PAGE_BREAK@@"
FRONT_TITLE = "Cover, table of contents and front matter"
BLOCK_TAGS = ["p", "div", "tr", "li", "h1", "h2", "h3", "h4", "h5", "h6", "table",
              "section", "article", "blockquote", "center", "dt", "dd"]
CELL_TAGS = ["td", "th"]

TOC_MAX_CHARS = 300
SUBSTANTIAL_CHARS = 1000

_WS = re.compile(r"\s+")
_PAGE_BREAK_STYLE = re.compile(r"(page-break-(before|after)\s*:\s*always)|(break-(before|after)\s*:\s*page)", re.I)
_HIDDEN_STYLE = re.compile(r"display\s*:\s*none", re.I)
_ITEM_RE = re.compile(r"^item\s+(\d{1,2}[a-c]?)\s*[\.:\-\u2013\u2014]?\s*(.*)$", re.I)
_ENDS_WITH_PAGE_NO = re.compile(r"\s\d{1,3}$")

TEN_K_ITEMS = {
    "1": "Business",
    "1A": "Risk Factors",
    "1B": "Unresolved Staff Comments",
    "1C": "Cybersecurity",
    "2": "Properties",
    "3": "Legal Proceedings",
    "4": "Mine Safety Disclosures",
    "5": "Market for Registrant's Common Equity, Related Stockholder Matters and Issuer Purchases of Equity Securities",
    "6": "[Reserved]",
    "7": "Management's Discussion and Analysis of Financial Condition and Results of Operations",
    "7A": "Quantitative and Qualitative Disclosures About Market Risk",
    "8": "Financial Statements and Supplementary Data",
    "9": "Changes in and Disagreements with Accountants on Accounting and Financial Disclosure",
    "9A": "Controls and Procedures",
    "9B": "Other Information",
    "9C": "Disclosure Regarding Foreign Jurisdictions that Prevent Inspections",
    "10": "Directors, Executive Officers and Corporate Governance",
    "11": "Executive Compensation",
    "12": "Security Ownership of Certain Beneficial Owners and Management and Related Stockholder Matters",
    "13": "Certain Relationships and Related Transactions, and Director Independence",
    "14": "Principal Accountant Fees and Services",
    "15": "Exhibits and Financial Statement Schedules",
    "16": "Form 10-K Summary",
}

# (heading prefix, section key) - order matters: more specific first.
PROXY_HEADINGS = [
    ("certain relationships and related", "related_person_transactions"),
    ("related person transactions", "related_person_transactions"),
    ("transactions with related persons", "related_person_transactions"),
    ("related party transactions", "related_person_transactions"),
    ("director independence", "director_independence"),
    ("corporate governance", "corporate_governance"),
    ("board leadership", "board_leadership"),
    ("committees of the board", "board_committees"),
    ("board committees", "board_committees"),
    ("audit committee report", "audit_committee_report"),
    ("audit committee", "audit_committee"),
    ("compensation committee", "compensation_committee"),
    ("nominating", "nominating_committee"),
    ("risk oversight", "risk_oversight"),
    ("board's role in risk", "risk_oversight"),
    ("compensation discussion and analysis", "cd_and_a"),
    ("summary compensation table", "summary_compensation_table"),
    ("executive compensation", "executive_compensation"),
    ("director compensation", "director_compensation"),
    ("security ownership", "security_ownership"),
    ("delinquent section 16", "section_16"),
    ("pay versus performance", "pay_versus_performance"),
    ("information about our directors", "directors"),
    ("director nominees", "directors"),
    ("election of directors", "directors"),
    ("executive officers", "executive_officers"),
]


class Paragraph(BaseModel):
    index: int
    page: int | None
    text: str


class Section(BaseModel):
    key: str
    title: str
    heading: str | None = None
    page_start: int | None
    page_end: int | None
    paragraphs: list[Paragraph]


class ParsedDocument(BaseModel):
    cik: str
    company: str
    form: str
    accession_no: str
    filing_date: date
    report_date: date | None
    url: str
    has_page_markers: bool
    page_count: int | None
    sections: list[Section]


def _prepare_soup(html: str) -> tuple[BeautifulSoup, int]:
    """Clean the HTML and insert line/page markers. Returns (soup, number of page breaks)."""
    soup = BeautifulSoup(html, "lxml")
    for tag in soup(["script", "style", "head", "noscript"]):
        tag.decompose()
    for comment in soup.find_all(string=lambda s: isinstance(s, Comment)):
        comment.extract()
    for tag in soup.find_all(lambda t: t.name == "ix:header"):
        tag.decompose()
    for tag in soup.find_all(style=_HIDDEN_STYLE):
        tag.decompose()

    # Collapse whitespace inside text nodes (source HTML wraps lines arbitrarily).
    for text_node in list(soup.find_all(string=True)):
        cleaned = _WS.sub(" ", str(text_node).replace("\xa0", " "))
        if cleaned != text_node:
            text_node.replace_with(cleaned)

    breaks = 0
    for tag in soup.find_all(style=_PAGE_BREAK_STYLE):
        marker = NavigableString(f"\n{PAGE_MARK}\n")
        if "after" in tag.get("style", "").lower():
            tag.insert_after(marker)
        else:
            tag.insert_before(marker)
        breaks += 1

    for br in soup.find_all("br"):
        br.replace_with("\n")
    for cell in soup.find_all(CELL_TAGS):
        cell.append(" | ")
    for block in soup.find_all(BLOCK_TAGS):
        block.append("\n")
    return soup, breaks


def _clean_line(line: str) -> str:
    line = _WS.sub(" ", line).strip()
    line = re.sub(r"(\s*\|\s*){2,}", " | ", line)
    line = re.sub(r"^(\|\s*)+", "", line)
    line = re.sub(r"(\s*\|)+$", "", line)
    return line.strip()


def _detect_heading(line: str, form: str) -> tuple[str, str] | None:
    """Return (section key, title) if the line is a section heading."""
    flat = _WS.sub(" ", line.replace("|", " ")).strip().replace("\u2019", "'")
    if len(flat) > 120 or _ENDS_WITH_PAGE_NO.search(flat):
        return None  # too long for a heading, or a table-of-contents row ending in a page number
    if form.upper().startswith("10-K"):
        match = _ITEM_RE.match(flat)
        if not match:
            return None
        item = match.group(1).upper()
        title = TEN_K_ITEMS.get(item) or match.group(2).strip() or f"Item {item}"
        return f"item_{item.lower()}", f"Item {item}. {title}"
    if len(flat) > 90:
        return None
    low = flat.lower()
    for prefix, key in PROXY_HEADINGS:
        if low.startswith(prefix):
            return key, flat
    return None


def _chars(section: dict) -> int:
    return sum(len(p.text) for p in section["paragraphs"])


def _toc_positions(sections: list[dict], form: str) -> set[int]:
    """Positions (in the section list) that are table-of-contents entries, not real sections."""
    if form.upper().startswith("10-K"):
        last: dict[str, int] = {}
        for i, sec in enumerate(sections):
            last[sec["key"]] = i
        return {i for i, sec in enumerate(sections) if sec["key"] != "front_matter" and last[sec["key"]] != i}

    first_big = next(
        (i for i, sec in enumerate(sections) if sec["key"] != "front_matter" and _chars(sec) >= SUBSTANTIAL_CHARS),
        None,
    )
    if first_big is None:
        return set()  # short document: nothing to treat as a table of contents
    return {
        i for i, sec in enumerate(sections)
        if sec["key"] != "front_matter" and i < first_big and _chars(sec) < TOC_MAX_CHARS
    }


def _fold_toc(sections: list[dict], form: str) -> list[dict]:
    toc = _toc_positions(sections, form)
    if not toc:
        return sections
    front = sections[0]
    for i in sorted(toc):
        sec = sections[i]
        if sec["heading"] is not None:
            front["paragraphs"].append(Paragraph(index=sec["heading_index"], page=sec["heading_page"], text=sec["heading"]))
        front["paragraphs"].extend(sec["paragraphs"])
    front["paragraphs"].sort(key=lambda p: p.index)
    return [sec for i, sec in enumerate(sections) if i not in toc]


def parse_filing(html: str, ref: FilingRef) -> ParsedDocument:
    soup, breaks = _prepare_soup(html)
    text = soup.get_text()
    del soup
    has_pages = breaks > 0

    page = 1
    index = 0
    sections: list[dict] = [{
        "key": "front_matter", "title": FRONT_TITLE, "heading": None, "heading_index": None,
        "heading_page": 1 if has_pages else None, "paragraphs": [],
    }]

    for raw in text.split("\n"):
        stripped = raw.strip()
        if stripped == PAGE_MARK:
            page += 1
            continue
        line = _clean_line(stripped)
        if not line:
            continue
        current_page = page if has_pages else None
        heading = _detect_heading(line, ref.form)
        if heading and heading[0] != sections[-1]["key"]:
            sections.append({
                "key": heading[0], "title": heading[1], "heading": line, "heading_index": index,
                "heading_page": current_page, "paragraphs": [],
            })
            index += 1
            continue
        sections[-1]["paragraphs"].append(Paragraph(index=index, page=current_page, text=line))
        index += 1

    sections = _fold_toc(sections, ref.form)

    built: list[Section] = []
    for sec in sections:
        paragraphs = sec["paragraphs"]
        if not paragraphs:
            continue
        pages = [p.page for p in paragraphs if p.page is not None]
        page_start = sec["heading_page"] if sec["heading_page"] is not None else (min(pages) if pages else None)
        built.append(Section(
            key=sec["key"],
            title=sec["title"],
            heading=sec["heading"],
            page_start=page_start,
            page_end=max(pages) if pages else None,
            paragraphs=paragraphs,
        ))

    return ParsedDocument(
        cik=ref.cik,
        company=ref.company,
        form=ref.form,
        accession_no=ref.accession_no,
        filing_date=ref.filing_date,
        report_date=ref.report_date,
        url=ref.url,
        has_page_markers=has_pages,
        page_count=page if has_pages else None,
        sections=built,
    )


def _main(argv: list[str]) -> int:
    from app.config import get_settings

    if len(argv) < 2:
        print("usage: python -m app.ingest.parse <TICKER|CIK> [--before YYYY-MM-DD]")
        return 2
    before = date.fromisoformat(argv[argv.index("--before") + 1]) if "--before" in argv else None

    settings = get_settings()
    out_dir = settings.cache_dir / "parsed"
    out_dir.mkdir(parents=True, exist_ok=True)
    try:
        with EdgarClient(settings.sec_user_agent, cache_dir=settings.cache_dir) as client:
            cik, name = client.lookup_company(argv[1])
            print(f"{name} (CIK {cik})")
            for ref in client.list_filings(cik, before=before):
                started = time.perf_counter()
                doc = parse_filing(client.fetch_document(ref), ref)
                out = out_dir / f"{ref.accession_no}.json"
                out.write_text(doc.model_dump_json(), encoding="utf-8")
                n_par = sum(len(s.paragraphs) for s in doc.sections)
                print(f"\n{ref.form} filed {ref.filing_date}  pages={doc.page_count}  sections={len(doc.sections)}  "
                      f"paragraphs={n_par:,}  {time.perf_counter() - started:.1f}s  -> {out.name}")
                for sec in doc.sections:
                    chars = sum(len(p.text) for p in sec.paragraphs)
                    print(f"    {sec.key:30} p.{sec.page_start}-{sec.page_end}  {chars:>9,} chars  {sec.title[:60]}")
    except EdgarError as exc:
        print(f"ERROR: {exc}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(_main(sys.argv))