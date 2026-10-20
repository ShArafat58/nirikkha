"""Tests for governance extraction with a fake LLM (no network)."""

from types import SimpleNamespace

from app.graph.extract import Chunk, dedupe, extract_chunk, normalize_name, quote_in_text

PASSAGE = ("Laura Izurieta, Chief Risk Officer, is responsible for leading our enterprise-wide risk management. "
           "John Smith chairs the Risk Committee and is also a director of Example Corp.")

CHUNK = Chunk(chunk_id="c1", accession_no="a1", section_key="executive_officers",
              section_title="EXECUTIVE OFFICERS", page_start=30, page_end=30, text=PASSAGE)


def fake_complete(relations):
    def complete(task, messages, json_mode=False, max_tokens=0, **kwargs):
        assert task == "extract" and json_mode is True
        assert "SVB" in messages[0]["content"]  # company injected into the versioned prompt
        return SimpleNamespace(data={"relations": relations}, input_tokens=100, output_tokens=50)
    return complete


def test_quote_verification():
    assert quote_in_text("chairs the  Risk Committee", PASSAGE)
    assert not quote_in_text("chairs the Audit Committee", PASSAGE)
    assert not quote_in_text("short", PASSAGE)


def test_extract_chunk_verifies_quotes_and_rejects_bad_types():
    relations = [
        {"person": "Laura Izurieta", "relation": "OFFICER_OF", "organization": "SVB", "title": "Chief Risk Officer",
         "quote": "Laura Izurieta, Chief Risk Officer, is responsible"},
        {"person": "John Smith", "relation": "BOARD_SEAT_ELSEWHERE", "organization": "Example Corp",
         "quote": "a director of Example Corp"},
        {"person": "John Smith", "relation": "BOARD_SEAT_ELSEWHERE", "organization": "Invented Inc",
         "quote": "a director of Invented Inc"},
        {"person": "Someone", "relation": "BEST_FRIEND_OF", "organization": "X", "quote": "irrelevant text here"},
    ]
    items, stats = extract_chunk(fake_complete(relations), "SVB", "DEF 14A", CHUNK)
    assert len(items) == 3
    assert [i.verified for i in items] == [True, True, False]
    assert stats == {"rejected": 1, "unverified": 1, "tokens": 150}
    assert items[0].page_start == 30 and items[0].chunk_id == "c1"


def test_normalize_name_and_dedupe():
    assert normalize_name("Ms. Laura  Izurieta.") == "Laura Izurieta"
    rel = {"relation": "OFFICER_OF", "organization": "SVB", "quote": "Laura Izurieta, Chief Risk Officer, is responsible"}
    items, _ = extract_chunk(fake_complete([{"person": "Laura Izurieta", **rel}, {"person": "Ms. Laura Izurieta", **rel}]),
                             "SVB", "DEF 14A", CHUNK)
    assert len(dedupe(items)) == 1

def test_table_quote_with_pipes_verifies():
    table_text = "Eric Benhamou\n| 66 | 2005 | 2 | X | C | X"
    assert quote_in_text("Eric Benhamou | 66 | 2005 | 2 | X | C", table_text)


def test_preceding_context_is_sent_but_not_used_for_verification():
    from app.graph.extract import build_messages

    msgs = build_messages("SVB", "DEF 14A", CHUNK, context="Name | Age | Audit | Risk")
    assert "PRECEDING CONTEXT" in msgs[1]["content"] and "Name | Age | Audit | Risk" in msgs[1]["content"]
    relations = [{"person": "X", "relation": "COMMITTEE_MEMBER", "organization": "Audit Committee",
                  "quote": "Name | Age | Audit | Risk"}]
    items, stats = extract_chunk(fake_complete(relations), "SVB", "DEF 14A", CHUNK, context="Name | Age | Audit | Risk")
    assert items[0].verified is False and stats["unverified"] == 1
