"""Unit tests for retrieval helpers (no database needed)."""

from datetime import date

from app.rag.search import build_filters, rrf_merge
from app.rag.store import to_pgvector


def test_rrf_rewards_items_found_by_both_searches():
    fused = rrf_merge({"vector": ["a", "b", "c"], "keyword": ["c", "a", "d"]}, limit=4)
    assert [cid for cid, _, _ in fused] == ["a", "c", "b", "d"]
    assert fused[0][2] == ["vector", "keyword"]
    assert fused[2][2] == ["vector"]


def test_rrf_limit():
    fused = rrf_merge({"vector": ["a", "b", "c"]}, limit=2)
    assert len(fused) == 2


def test_filters_freeze_evidence_and_normalize_cik():
    where, params = build_filters("719739", date(2023, 3, 10), ["10-K", "DEF 14A"])
    assert "f.filing_date < %s" in where
    assert params == ["0000719739", date(2023, 3, 10), ["10-K", "DEF 14A"]]


def test_no_filters():
    where, params = build_filters(None, None, None)
    assert where == "true" and params == []


def test_pgvector_literal():
    assert to_pgvector([0.5, -0.25]) == "[0.500000,-0.250000]"

def test_keyword_query_uses_or():
    from app.rag.search import to_or_query

    assert to_or_query("unrealized losses on HTM securities") == "unrealized or losses or on or HTM or securities"
    assert to_or_query("$120,000 threshold") == "$120,000 or threshold"
