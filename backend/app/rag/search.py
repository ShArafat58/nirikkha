"""Retrieval over Supabase pgvector: vector search, keyword (full-text) search and hybrid (RRF).

Filters: company (CIK), filed strictly before a date (Replay evidence freeze), form types.

Run directly:
    python -m app.rag.search "unrealized losses on held-to-maturity securities" --cik 719739 --before 2023-03-10
    python -m app.rag.search "related person transactions" --mode keyword --forms "DEF 14A"
"""

from __future__ import annotations

import argparse
import re
import sys
from datetime import date

import psycopg
from pydantic import BaseModel

from app.db import DatabaseError, connect
from app.ingest.edgar import normalize_cik
from app.rag.store import to_pgvector

RRF_K = 60
CANDIDATES = 30

SELECT_COLS = (
    "c.chunk_id, f.accession_no, f.company, f.form, f.filing_date, "
    "c.section_title, c.page_start, c.page_end, c.text"
)


class Hit(BaseModel):
    chunk_id: str
    accession_no: str
    company: str
    form: str
    filing_date: date
    section_title: str
    page_start: int | None
    page_end: int | None
    text: str
    score: float
    sources: list[str] = []


def rrf_merge(rankings: dict[str, list[str]], k: int = RRF_K, limit: int = 10) -> list[tuple[str, float, list[str]]]:
    """Reciprocal Rank Fusion: score = sum over lists of 1 / (k + rank)."""
    scores: dict[str, float] = {}
    sources: dict[str, list[str]] = {}
    for name, ids in rankings.items():
        for rank, chunk_id in enumerate(ids, start=1):
            scores[chunk_id] = scores.get(chunk_id, 0.0) + 1.0 / (k + rank)
            sources.setdefault(chunk_id, []).append(name)
    ordered = sorted(scores.items(), key=lambda kv: (-kv[1], kv[0]))[:limit]
    return [(chunk_id, score, sources[chunk_id]) for chunk_id, score in ordered]


def build_filters(cik: str | None, before: date | None, forms: list[str] | None) -> tuple[str, list]:
    clauses: list[str] = []
    params: list = []
    if cik:
        clauses.append("f.cik = %s")
        params.append(normalize_cik(cik))
    if before:
        clauses.append("f.filing_date < %s")
        params.append(before)
    if forms:
        clauses.append("f.form = any(%s)")
        params.append(list(forms))
    return (" and ".join(clauses) or "true"), params


def to_or_query(query: str) -> str:
    """Join words with OR for websearch_to_tsquery, so a passage needs only some of the words."""
    words = re.findall(r"[A-Za-z0-9$][A-Za-z0-9$.,%-]*", query)
    return " or ".join(words) if words else query


def _rows_to_hits(rows, source: str) -> list[Hit]:
    return [
        Hit(chunk_id=r[0], accession_no=r[1], company=r[2], form=r[3], filing_date=r[4], section_title=r[5],
            page_start=r[6], page_end=r[7], text=r[8], score=float(r[9]), sources=[source])
        for r in rows
    ]


def vector_search(conn: psycopg.Connection, query_vector: list[float], k: int = CANDIDATES,
                  cik: str | None = None, before: date | None = None, forms: list[str] | None = None) -> list[Hit]:
    where, params = build_filters(cik, before, forms)
    vec = to_pgvector(query_vector)
    sql = (
        f"select {SELECT_COLS}, 1 - (c.embedding <=> %s::vector) as score "
        f"from chunks c join filings f using (accession_no) "
        f"where c.embedding is not null and {where} "
        f"order by c.embedding <=> %s::vector limit %s"
    )
    with conn.transaction():
        conn.execute("set local hnsw.ef_search = 100")
        try:
            with conn.transaction():  # pgvector >= 0.8: keep results when filters are selective
                conn.execute("set local hnsw.iterative_scan = relaxed_order")
        except psycopg.Error:
            pass
        rows = conn.execute(sql, [vec, *params, vec, k]).fetchall()
    return _rows_to_hits(rows, "vector")


def keyword_search(conn: psycopg.Connection, query: str, k: int = CANDIDATES,
                   cik: str | None = None, before: date | None = None, forms: list[str] | None = None) -> list[Hit]:
    where, params = build_filters(cik, before, forms)
    sql = (
        f"select {SELECT_COLS}, ts_rank_cd(c.tsv, q) as score "
        f"from chunks c join filings f using (accession_no), websearch_to_tsquery('english', %s) q "
        f"where c.tsv @@ q and {where} "
        f"order by score desc limit %s"
    )
    rows = conn.execute(sql, [to_or_query(query), *params, k]).fetchall()
    return _rows_to_hits(rows, "keyword")


def hybrid_search(conn: psycopg.Connection, query: str, query_vector: list[float], k: int = 8,
                  cik: str | None = None, before: date | None = None, forms: list[str] | None = None) -> list[Hit]:
    vec_hits = vector_search(conn, query_vector, CANDIDATES, cik, before, forms)
    kw_hits = keyword_search(conn, query, CANDIDATES, cik, before, forms)
    by_id = {h.chunk_id: h for h in kw_hits}
    by_id.update({h.chunk_id: h for h in vec_hits})
    fused = rrf_merge({"vector": [h.chunk_id for h in vec_hits], "keyword": [h.chunk_id for h in kw_hits]}, limit=k)
    results = []
    for chunk_id, score, sources in fused:
        hit = by_id[chunk_id].model_copy(update={"score": score, "sources": sources})
        results.append(hit)
    return results


def _main(argv: list[str]) -> int:
    from app.config import get_settings
    from app.rag.embeddings import EmbeddingError, GeminiEmbedder

    parser = argparse.ArgumentParser(description="Search filings in Supabase")
    parser.add_argument("query")
    parser.add_argument("--cik")
    parser.add_argument("--before", type=date.fromisoformat)
    parser.add_argument("--forms", nargs="*")
    parser.add_argument("--mode", choices=["vector", "keyword", "hybrid"], default="hybrid")
    parser.add_argument("-k", type=int, default=5)
    args = parser.parse_args(argv[1:])

    s = get_settings()
    try:
        with connect() as conn:
            if args.mode == "keyword":
                hits = keyword_search(conn, args.query, args.k, args.cik, args.before, args.forms)
            else:
                with GeminiEmbedder(s.gemini_api_key, s.embedding_model, s.embedding_dim, cache_dir=s.cache_dir) as emb:
                    qvec = emb.embed_query(args.query)
                if args.mode == "vector":
                    hits = vector_search(conn, qvec, args.k, args.cik, args.before, args.forms)
                else:
                    hits = hybrid_search(conn, args.query, qvec, args.k, args.cik, args.before, args.forms)
    except (DatabaseError, EmbeddingError) as exc:
        print(f"ERROR: {exc}")
        return 1

    print(f'"{args.query}"  mode={args.mode}  cik={args.cik}  before={args.before}  forms={args.forms}')
    for i, h in enumerate(hits, start=1):
        pages = f"p.{h.page_start}-{h.page_end}" if h.page_start else "p.n/a"
        snippet = " ".join(h.text.split())[:220]
        print(f"\n{i}. [{'+'.join(h.sources)} {h.score:.4f}] {h.company} {h.form} filed {h.filing_date} | {h.section_title[:50]} | {pages}")
        print(f"   {snippet}...")
    if not hits:
        print("No results.")
    return 0


if __name__ == "__main__":
    sys.exit(_main(sys.argv))