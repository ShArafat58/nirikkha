"""Retrieval embeddings: local (default, unlimited) or Gemini (free tier, 1,000 requests/day).

Default: BAAI/bge-small-en-v1.5 via fastembed (ONNX, CPU, 384 dims). Free, no quota, and
documents never leave the machine - this is also our private mode.
Optional: Gemini gemini-embedding-001 (EMBEDDING_PROVIDER=gemini, EMBEDDING_DIM=768).
We measured the Gemini free-tier limit on 2026-10-20: 1,000 embed requests per day per
project (each text in a batch counts), which is why local is the default.

All vectors are L2-normalised. Both providers cache vectors on disk.

Run directly:
    python -m app.rag.embeddings              # embed all .cache/chunks/*.jsonl -> .cache/vectors/
    python -m app.rag.embeddings --only "0000719739,0001193125"
    python -m app.rag.embeddings --list-models   # Gemini only
"""

from __future__ import annotations

import hashlib
import json
import math
import sys
import time
from collections import deque
from pathlib import Path
from typing import Any, Callable

import httpx

API_BASE = "https://generativelanguage.googleapis.com/v1beta"
MAX_BATCH = 100
RETRY_STATUS = {429, 500, 502, 503, 504}


class EmbeddingError(RuntimeError):
    """Raised with a clear message when embedding fails."""


def estimate_tokens(text: str) -> int:
    """Rough token estimate (about 3 characters per token; conservative for numeric tables)."""
    return max(1, len(text) // 3)


def _normalize(vector: list[float]) -> list[float]:
    norm = math.sqrt(sum(x * x for x in vector))
    return [x / norm for x in vector] if norm else vector


class _DiskCache:
    def __init__(self, cache_dir: Path | None, namespace: str) -> None:
        self.cache_dir = cache_dir
        self.namespace = namespace

    def key(self, text: str, task: str) -> str:
        return hashlib.sha256(f"{self.namespace}|{task}|{text}".encode("utf-8")).hexdigest()

    def _path(self, key: str) -> Path | None:
        if self.cache_dir is None:
            return None
        return self.cache_dir / "embeddings" / key[:2] / f"{key}.json"

    def get(self, key: str) -> list[float] | None:
        path = self._path(key)
        if path is not None and path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
        return None

    def put(self, key: str, vector: list[float]) -> None:
        path = self._path(key)
        if path is not None:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(vector), encoding="utf-8")


class LocalEmbedder:
    """fastembed (ONNX) embedding model running on the local CPU."""

    provider = "local"

    def __init__(self, model_name: str = "BAAI/bge-small-en-v1.5", cache_dir: Path | None = None,
                 model: Any = None, batch_size: int = 32) -> None:
        if model is None:
            try:
                from fastembed import TextEmbedding
            except ImportError as exc:
                raise EmbeddingError("fastembed is not installed. Run: pip install -r requirements-ingest.txt") from exc
            model = TextEmbedding(model_name=model_name)
        self.model = model_name
        self._model = model
        self._cache = _DiskCache(cache_dir, f"local|{model_name}")
        self.batch_size = batch_size
        self.stats = {"requests": 0, "embedded": 0, "cached": 0, "tokens_est": 0}

    def close(self) -> None:
        pass

    def __enter__(self) -> "LocalEmbedder":
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    def embed(self, texts: list[str], task: str = "RETRIEVAL_DOCUMENT") -> list[list[float]]:
        results: list[list[float] | None] = [None] * len(texts)
        pending: list[tuple[int, str, str]] = []
        for i, text in enumerate(texts):
            key = self._cache.key(text, task)
            cached = self._cache.get(key)
            if cached is not None:
                results[i] = cached
                self.stats["cached"] += 1
            else:
                pending.append((i, text, key))
        if pending:
            items = [t for _, t, _ in pending]
            if task == "RETRIEVAL_QUERY":
                raw = self._model.query_embed(items)
            else:
                raw = self._model.passage_embed(items, batch_size=self.batch_size)
            for (i, text, key), vector in zip(pending, raw):
                normalized = _normalize([float(x) for x in vector])
                results[i] = normalized
                self._cache.put(key, normalized)
                self.stats["embedded"] += 1
                self.stats["tokens_est"] += estimate_tokens(text)
        return [r for r in results if r is not None]

    def embed_query(self, text: str) -> list[float]:
        return self.embed([text], task="RETRIEVAL_QUERY")[0]


class GeminiEmbedder:
    """Gemini embedding API with batching, rate limiting, retries and a disk cache."""

    provider = "gemini"

    def __init__(
        self,
        api_key: str,
        model: str = "gemini-embedding-001",
        dim: int = 768,
        tpm: int = 25000,
        rpm: int = 90,
        cache_dir: Path | None = None,
        transport: httpx.BaseTransport | None = None,
        max_retries: int = 5,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        if not api_key:
            raise EmbeddingError("GEMINI_API_KEY is not set.")
        self.model = model.removeprefix("models/")
        self.dim = dim
        self.tpm = tpm
        self.rpm = rpm
        self.max_retries = max_retries
        self._sleep = sleep
        self._window: deque[tuple[float, int]] = deque()
        self._cache = _DiskCache(cache_dir, f"{self.model}|{self.dim}")
        self._client = httpx.Client(
            base_url=API_BASE,
            headers={"x-goog-api-key": api_key},
            timeout=60.0,
            transport=transport,
        )
        self.stats = {"requests": 0, "embedded": 0, "cached": 0, "tokens_est": 0}

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> "GeminiEmbedder":
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    def _wait_for_budget(self, tokens: int) -> None:
        while True:
            now = time.monotonic()
            while self._window and now - self._window[0][0] > 60:
                self._window.popleft()
            used = sum(t for _, t in self._window)
            if not self._window or (len(self._window) < self.rpm and used + tokens <= self.tpm):
                self._window.append((now, tokens))
                return
            wait = 60 - (now - self._window[0][0]) + 0.5
            self._sleep(max(wait, 0.5))

    def _post_batch(self, texts: list[str], task: str) -> list[list[float]]:
        body = {
            "requests": [
                {
                    "model": f"models/{self.model}",
                    "content": {"parts": [{"text": t}]},
                    "taskType": task,
                    "outputDimensionality": self.dim,
                }
                for t in texts
            ]
        }
        tokens = sum(estimate_tokens(t) for t in texts)
        last_error = "unknown error"
        for attempt in range(self.max_retries):
            self._wait_for_budget(tokens)
            try:
                resp = self._client.post(f"/models/{self.model}:batchEmbedContents", json=body)
            except httpx.HTTPError as exc:
                last_error = f"network error: {exc}"
            else:
                self.stats["requests"] += 1
                if resp.status_code == 200:
                    embeddings = resp.json().get("embeddings", [])
                    if len(embeddings) != len(texts):
                        raise EmbeddingError("Gemini returned a different number of embeddings than requested.")
                    self.stats["tokens_est"] += tokens
                    return [_normalize([float(x) for x in e["values"]]) for e in embeddings]
                last_error = f"HTTP {resp.status_code}: {resp.text[:400]}"
                if resp.status_code not in RETRY_STATUS:
                    break
            self._sleep(min(10 * (attempt + 1), 60))
        raise EmbeddingError(f"Gemini embedding failed ({last_error})")

    def embed(self, texts: list[str], task: str = "RETRIEVAL_DOCUMENT") -> list[list[float]]:
        results: list[list[float] | None] = [None] * len(texts)
        pending: list[tuple[int, str, str]] = []
        for i, text in enumerate(texts):
            key = self._cache.key(text, task)
            cached = self._cache.get(key)
            if cached is not None:
                results[i] = cached
                self.stats["cached"] += 1
            else:
                pending.append((i, text, key))

        budget = int(self.tpm * 0.8)
        batch: list[tuple[int, str, str]] = []
        batch_tokens = 0

        def flush(items: list[tuple[int, str, str]]) -> None:
            vectors = self._post_batch([t for _, t, _ in items], task)
            for (i, _, key), vector in zip(items, vectors):
                results[i] = vector
                self._cache.put(key, vector)
                self.stats["embedded"] += 1

        for item in pending:
            tokens = estimate_tokens(item[1])
            if batch and (len(batch) >= MAX_BATCH or batch_tokens + tokens > budget):
                flush(batch)
                batch, batch_tokens = [], 0
            batch.append(item)
            batch_tokens += tokens
        if batch:
            flush(batch)
        return [r for r in results if r is not None]

    def embed_query(self, text: str) -> list[float]:
        return self.embed([text], task="RETRIEVAL_QUERY")[0]

    def list_embedding_models(self) -> list[str]:
        resp = self._client.get("/models", params={"pageSize": 1000})
        if resp.status_code != 200:
            raise EmbeddingError(f"Could not list models (HTTP {resp.status_code}).")
        return [
            m["name"]
            for m in resp.json().get("models", [])
            if "embedContent" in m.get("supportedGenerationMethods", [])
        ]


def get_embedder(settings: Any) -> LocalEmbedder | GeminiEmbedder:
    provider = settings.embedding_provider.lower()
    if provider == "local":
        return LocalEmbedder(settings.local_embedding_model, cache_dir=settings.cache_dir)
    if provider == "gemini":
        return GeminiEmbedder(
            settings.gemini_api_key, settings.embedding_model, settings.embedding_dim,
            settings.gemini_embed_tpm, settings.gemini_embed_rpm, cache_dir=settings.cache_dir,
        )
    raise EmbeddingError(f"Unknown EMBEDDING_PROVIDER: {settings.embedding_provider!r} (use 'local' or 'gemini').")


def _main(argv: list[str]) -> int:
    from app.config import get_settings

    s = get_settings()
    try:
        with get_embedder(s) as embedder:
            if "--list-models" in argv:
                if not isinstance(embedder, GeminiEmbedder):
                    print("--list-models works only with EMBEDDING_PROVIDER=gemini")
                    return 1
                for name in embedder.list_embedding_models():
                    print(name)
                return 0

            chunk_dir = s.cache_dir / "chunks"
            out_dir = s.cache_dir / "vectors"
            out_dir.mkdir(parents=True, exist_ok=True)
            files = sorted(chunk_dir.glob("*.jsonl"))
            if "--only" in argv:  # comma-separated accession prefixes (quote it in PowerShell)
                prefixes = argv[argv.index("--only") + 1].split(",")
                files = [f for f in files if any(f.stem.startswith(p) for p in prefixes)]
            if not files:
                print(f"No chunk files in {chunk_dir}. Run: python -m app.ingest.chunk")
                return 1
            print(f"Embedding with {embedder.provider}: {embedder.model}")
            total_started = time.perf_counter()
            for path in files:
                started = time.perf_counter()
                rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
                vectors = embedder.embed([r["embed_text"] for r in rows])
                dims = len(vectors[0]) if vectors else 0
                with (out_dir / path.name).open("w", encoding="utf-8") as f:
                    for row, vector in zip(rows, vectors):
                        f.write(json.dumps({"chunk_id": row["chunk_id"], "embedding": vector}) + "\n")
                print(f"  {path.stem}  chunks={len(rows):4}  dims={dims}  {time.perf_counter() - started:6.1f}s")
            st = embedder.stats
            print(f"Done in {time.perf_counter() - total_started:.0f}s. New embeddings={st['embedded']}, "
                  f"from cache={st['cached']}, est. tokens={st['tokens_est']:,} (cost: $0)")
    except EmbeddingError as exc:
        print(f"ERROR: {exc}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(_main(sys.argv))