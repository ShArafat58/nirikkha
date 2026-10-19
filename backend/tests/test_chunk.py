"""Tests for semantic + contextual chunking, using a fake embedder (no model download)."""

from datetime import date

from app.ingest.chunk import MAX_CHARS, chunk_document
from app.ingest.parse import Paragraph, ParsedDocument, Section


def fake_embed(texts):
    # Two "topics": deposits vs compensation.
    return [[1.0, 0.0] if "deposit" in t.lower() else [0.0, 1.0] for t in texts]


def para(i, text, page=17):
    return Paragraph(index=i, page=page, text=text)


def make_doc(sections):
    return ParsedDocument(
        cik="0000719739",
        company="SVB FINANCIAL GROUP",
        form="10-K",
        accession_no="0000719739-23-000021",
        filing_date=date(2023, 2, 24),
        report_date=date(2022, 12, 31),
        url="https://example.invalid/x.htm",
        has_page_markers=True,
        page_count=181,
        sections=sections,
    )


DEPOSIT = "Our deposit base is concentrated in technology and life science clients. " * 4
COMP = "Executive pay is linked to long-term performance and shareholder returns. " * 4


def test_semantic_break_at_topic_shift():
    paras = [para(i, DEPOSIT) for i in range(4)] + [para(i, COMP, page=18) for i in range(4, 8)]
    sec = Section(key="item_1a", title="Item 1A. Risk Factors", page_start=17, page_end=18, paragraphs=paras)
    chunks = chunk_document(make_doc([sec]), fake_embed)
    assert len(chunks) == 2
    assert "deposit" in chunks[0].text.lower() and "pay" not in chunks[0].text.lower()
    assert "pay" in chunks[1].text.lower()
    assert (chunks[0].paragraph_start, chunks[0].paragraph_end) == (0, 3)


def test_contextual_header_has_company_form_section_pages():
    paras = [para(0, DEPOSIT), para(1, DEPOSIT, page=18)]
    sec = Section(key="item_1a", title="Item 1A. Risk Factors", page_start=17, page_end=18, paragraphs=paras)
    chunk = chunk_document(make_doc([sec]), fake_embed)[0]
    assert chunk.context_header == (
        "SVB FINANCIAL GROUP | 10-K filed 2023-02-24, period 2022-12-31 | Item 1A. Risk Factors | pages 17-18"
    )
    assert chunk.embed_text.startswith(chunk.context_header)
    assert (chunk.page_start, chunk.page_end) == (17, 18)


def test_chunks_never_cross_sections():
    s1 = Section(key="item_1", title="Item 1. Business", page_start=6, page_end=6, paragraphs=[para(0, "We bank startups.", 6)])
    s2 = Section(key="item_1a", title="Item 1A. Risk Factors", page_start=17, page_end=17, paragraphs=[para(1, "Rates may rise.")])
    chunks = chunk_document(make_doc([s1, s2]), fake_embed)
    assert [c.section_key for c in chunks] == ["item_1", "item_1a"]


def test_oversized_paragraph_is_split_within_limit():
    huge = "Interest rate risk could reduce the value of our securities portfolio. " * 150
    sec = Section(key="item_7a", title="Item 7A. Market Risk", page_start=89, page_end=89, paragraphs=[para(0, huge, 89)])
    chunks = chunk_document(make_doc([sec]), fake_embed)
    assert len(chunks) > 1
    assert all(c.char_count <= MAX_CHARS for c in chunks)


def test_exact_duplicate_text_is_kept_once():
    s1 = Section(key="item_10", title="Item 10", page_start=175, page_end=175, paragraphs=[para(0, "Incorporated by reference to the proxy.", 175)])
    s2 = Section(key="item_11", title="Item 11", page_start=175, page_end=175, paragraphs=[para(1, "Incorporated by reference to the proxy.", 175)])
    chunks = chunk_document(make_doc([s1, s2]), fake_embed)
    assert len(chunks) == 1


def test_size_only_fallback_without_embedder():
    paras = [para(i, DEPOSIT) for i in range(12)]
    sec = Section(key="item_1a", title="Item 1A. Risk Factors", page_start=17, page_end=17, paragraphs=paras)
    chunks = chunk_document(make_doc([sec]), None)
    assert len(chunks) >= 2
    assert all(c.char_count <= MAX_CHARS for c in chunks)