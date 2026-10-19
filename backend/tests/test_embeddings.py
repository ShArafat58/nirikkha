"""Offline tests for the Gemini embedder (fake API, no network)."""

import json

import httpx
import pytest

from app.rag.embeddings import EmbeddingError, GeminiEmbedder


def make_embedder(seen, tmp_path=None, fail_first=0, dim=4):
    state = {"fails": fail_first}

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        if state["fails"] > 0:
            state["fails"] -= 1
            return httpx.Response(429, json={"error": "rate limited"})
        body = json.loads(request.content)
        n = len(body["requests"])
        return httpx.Response(200, json={"embeddings": [{"values": [3.0, 4.0] + [0.0] * (dim - 2)} for _ in range(n)]})

    return GeminiEmbedder(
        "test-key", dim=dim, tpm=10_000_000, rpm=10_000, cache_dir=tmp_path,
        transport=httpx.MockTransport(handler), sleep=lambda s: None,
    )


def test_missing_key_raises():
    with pytest.raises(EmbeddingError):
        GeminiEmbedder("")


def test_vectors_are_normalized_and_request_is_correct():
    seen = []
    emb = make_embedder(seen)
    vectors = emb.embed(["deposit concentration risk"])
    assert vectors == [[0.6, 0.8, 0.0, 0.0]]
    req = seen[0]
    assert req.headers["x-goog-api-key"] == "test-key"
    assert "key=" not in str(req.url)
    body = json.loads(req.content)["requests"][0]
    assert body["taskType"] == "RETRIEVAL_DOCUMENT"
    assert body["outputDimensionality"] == 4


def test_query_uses_query_task_type():
    seen = []
    make_embedder(seen).embed_query("who are the independent directors?")
    assert json.loads(seen[0].content)["requests"][0]["taskType"] == "RETRIEVAL_QUERY"


def test_batches_of_at_most_100():
    seen = []
    emb = make_embedder(seen)
    vectors = emb.embed([f"text {i}" for i in range(250)])
    assert len(vectors) == 250
    assert len(seen) == 3


def test_cache_avoids_second_request(tmp_path):
    seen = []
    emb = make_embedder(seen, tmp_path)
    emb.embed(["same text"])
    emb.embed(["same text"])
    assert len(seen) == 1
    assert emb.stats["cached"] == 1


def test_retries_after_rate_limit():
    seen = []
    emb = make_embedder(seen, fail_first=2)
    assert len(emb.embed(["retry me"])) == 1
    assert len(seen) == 3

class FakeLocalModel:
    def __init__(self):
        self.calls = []

    def passage_embed(self, texts, batch_size=32):
        texts = list(texts)
        self.calls.append(("passage", texts))
        return [[3.0, 4.0] for _ in texts]

    def query_embed(self, texts):
        texts = [texts] if isinstance(texts, str) else list(texts)
        self.calls.append(("query", texts))
        return [[0.0, 2.0] for _ in texts]


def test_local_embedder_normalizes_and_caches(tmp_path):
    from app.rag.embeddings import LocalEmbedder

    model = FakeLocalModel()
    emb = LocalEmbedder(cache_dir=tmp_path, model=model)
    assert emb.embed(["a", "b"]) == [[0.6, 0.8], [0.6, 0.8]]
    emb.embed(["a"])
    assert len(model.calls) == 1
    assert emb.stats["cached"] == 1


def test_local_query_uses_query_embedding():
    from app.rag.embeddings import LocalEmbedder

    model = FakeLocalModel()
    assert LocalEmbedder(model=model).embed_query("who is independent?") == [0.0, 1.0]
    assert model.calls[0][0] == "query"


def test_unknown_provider_raises():
    from types import SimpleNamespace

    from app.rag.embeddings import get_embedder

    with pytest.raises(EmbeddingError):
        get_embedder(SimpleNamespace(embedding_provider="other"))
