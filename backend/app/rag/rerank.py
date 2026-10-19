"""Cross-encoder reranking of retrieved passages (local, fastembed / ONNX).

A cross-encoder reads the query and a passage together and scores how well the passage
answers the query. It is slower than embedding search, so we only re-score the top
hybrid candidates (RERANK_CANDIDATES, default 20).
"""

from __future__ import annotations

from typing import Any

from app.rag.search import Hit


class RerankError(RuntimeError):
    """Raised with a clear message when reranking is unavailable."""


class CrossEncoderReranker:
    def __init__(self, model_name: str = "Xenova/ms-marco-MiniLM-L-6-v2", model: Any = None,
                 max_chars: int = 1500) -> None:
        if model is None:
            try:
                from fastembed.rerank.cross_encoder import TextCrossEncoder
            except ImportError as exc:
                raise RerankError("fastembed is not installed. Run: pip install -r requirements-ingest.txt") from exc
            model = TextCrossEncoder(model_name=model_name)
        self.model_name = model_name
        self._model = model
        self.max_chars = max_chars

    def rerank(self, query: str, hits: list[Hit], top_k: int | None = None) -> list[Hit]:
        if not hits:
            return []
        documents = [f"{h.section_title}\n{h.text[: self.max_chars]}" for h in hits]
        scores = [float(s) for s in self._model.rerank(query, documents)]
        ranked = sorted(zip(hits, scores), key=lambda pair: -pair[1])
        result = [h.model_copy(update={"score": score, "sources": [*h.sources, "rerank"]}) for h, score in ranked]
        return result[:top_k] if top_k else result