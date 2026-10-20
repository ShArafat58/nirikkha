"""Retrieval pipeline used by the agents: embed query -> hybrid search -> cross-encoder rerank.

Models and the database connection are opened once per process and reused
(the connection is reopened automatically if it drops).

Run directly (shows the rank before reranking as "was #n"):
    python -m app.rag.retrieve "related person transactions with directors" --cik 719739 --forms "DEF 14A"
    python -m app.rag.retrieve "interest rate risk" --cik 719739 --before 2023-03-10 --repeat 2
"""

from __future__ import annotations

import argparse
import sys
import time
from datetime import date

import psycopg

from app.config import get_settings
from app.db import DatabaseError, open_connection, tune_session
from app.rag.embeddings import EmbeddingError, get_embedder
from app.rag.rerank import CrossEncoderReranker, RerankError
from app.rag.search import Hit, hybrid_search

_embedder = None
_reranker: CrossEncoderReranker | None = None
_conn: psycopg.Connection | None = None


def _get_embedder():
    global _embedder
    if _embedder is None:
        _embedder = get_embedder(get_settings())
    return _embedder


def _get_reranker() -> CrossEncoderReranker:
    global _reranker
    if _reranker is None:
        _reranker = CrossEncoderReranker(get_settings().reranker_model)
    return _reranker


def _get_conn() -> psycopg.Connection:
    global _conn
    if _conn is None or _conn.closed or _conn.broken:
        _conn = open_connection(autocommit=True)
        tune_session(_conn)
    return _conn


def _hybrid(query: str, query_vector: list[float], k: int, cik, before, forms) -> list[Hit]:
    global _conn
    try:
        return hybrid_search(_get_conn(), query, query_vector, k, cik, before, forms)
    except psycopg.OperationalError:
        _conn = None  # connection dropped (e.g. pooler timeout): reconnect once
        return hybrid_search(_get_conn(), query, query_vector, k, cik, before, forms)


def retrieve(query: str, k: int = 8, cik: str | None = None, before: date | None = None,
             forms: list[str] | None = None, rerank: bool = True) -> tuple[list[Hit], dict]:
    """Return the top-k evidence passages and timings in milliseconds."""
    settings = get_settings()
    rerank = rerank and settings.rerank_enabled
    timings: dict[str, int] = {}

    started = time.perf_counter()
    query_vector = _get_embedder().embed_query(query)
    timings["embed_ms"] = int((time.perf_counter() - started) * 1000)

    started = time.perf_counter()
    hits = _hybrid(query, query_vector, settings.rerank_candidates if rerank else k, cik, before, forms)
    timings["search_ms"] = int((time.perf_counter() - started) * 1000)

    if rerank and hits:
        started = time.perf_counter()
        hits = _get_reranker().rerank(query, hits, top_k=k)
        timings["rerank_ms"] = int((time.perf_counter() - started) * 1000)
    return hits[:k], timings


def _main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Retrieve evidence passages")
    parser.add_argument("query")
    parser.add_argument("--cik")
    parser.add_argument("--before", type=date.fromisoformat)
    parser.add_argument("--forms", nargs="*")
    parser.add_argument("--no-rerank", action="store_true")
    parser.add_argument("-k", type=int, default=5)
    parser.add_argument("--repeat", type=int, default=1, help="run N times to show warm timings")
    args = parser.parse_args(argv[1:])

    try:
        for run in range(1, args.repeat + 1):
            if args.no_rerank:
                hits, timings = retrieve(args.query, args.k, args.cik, args.before, args.forms, rerank=False)
                before_rank: dict[str, int] = {}
            else:
                candidates, timings = retrieve(args.query, get_settings().rerank_candidates, args.cik,
                                               args.before, args.forms, rerank=False)
                before_rank = {h.chunk_id: i for i, h in enumerate(candidates, start=1)}
                started = time.perf_counter()
                hits = _get_reranker().rerank(args.query, candidates, top_k=args.k)
                timings["rerank_ms"] = int((time.perf_counter() - started) * 1000)
            print(f"run {run}: timings={timings}")
    except (DatabaseError, EmbeddingError, RerankError) as exc:
        print(f"ERROR: {exc}")
        return 1

    print(f'"{args.query}"  rerank={not args.no_rerank}')
    for i, h in enumerate(hits, start=1):
        pages = f"p.{h.page_start}-{h.page_end}" if h.page_start else "p.n/a"
        was = f" (was #{before_rank[h.chunk_id]})" if h.chunk_id in before_rank else ""
        snippet = " ".join(h.text.split())[:200]
        print(f"\n{i}.{was} [{'+'.join(h.sources)} {h.score:.3f}] {h.company} {h.form} filed {h.filing_date} | {h.section_title[:50]} | {pages}")
        print(f"   {snippet}...")
    if not hits:
        print("No results.")
    return 0


if __name__ == "__main__":
    sys.exit(_main(sys.argv))