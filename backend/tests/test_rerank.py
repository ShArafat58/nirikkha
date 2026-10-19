"""Tests for the cross-encoder reranker with a fake model (no download)."""

from datetime import date

from app.rag.rerank import CrossEncoderReranker
from app.rag.search import Hit


class FakeCrossEncoder:
    def rerank(self, query, documents):
        # Higher score when the document mentions "related".
        return [10.0 if "related" in d.lower() else 1.0 for d in documents]


def make_hit(chunk_id, text, title="Section"):
    return Hit(chunk_id=chunk_id, accession_no="a", company="SVB", form="DEF 14A", filing_date=date(2022, 3, 4),
               section_title=title, page_start=25, page_end=25, text=text, score=0.03, sources=["vector"])


def test_rerank_moves_relevant_passage_to_top():
    hits = [make_hit("1", "Director compensation is competitive."),
            make_hit("2", "Our related party transactions policy covers Item 404.")]
    ranked = CrossEncoderReranker(model=FakeCrossEncoder()).rerank("related person transactions", hits)
    assert [h.chunk_id for h in ranked] == ["2", "1"]
    assert ranked[0].score == 10.0
    assert ranked[0].sources == ["vector", "rerank"]


def test_rerank_top_k_and_empty():
    reranker = CrossEncoderReranker(model=FakeCrossEncoder())
    hits = [make_hit(str(i), "text") for i in range(5)]
    assert len(reranker.rerank("q", hits, top_k=2)) == 2
    assert reranker.rerank("q", []) == []