# PROGRESS - Nirikkha

Last updated: 2026-10-20 04:10 (Day 2 COMPLETE)

## Decisions
- Product name: **Nirikkha** - tagline "Trust less, Verify more". Challenge: GovernanceIQ.
- Local path: `D:\AI_Buildfest\Nirikkha`
- GitHub: https://github.com/ShArafat58/nirikkha (public)
- Machine: Windows, 16 GB RAM, Intel UHD (no NVIDIA GPU) -> local models CPU-only; fine-tuning on Colab/Kaggle.
- Backend host: Render free web service (Python 3, root `backend`). Auto-deploy not triggering -> Manual Deploy -> Deploy latest commit.
- Frontend: Next.js 16.4.2 + Tailwind + TypeScript on Vercel (root `frontend`), mock mode via `NEXT_PUBLIC_USE_MOCK`.
- Graph DB: Neo4j AuraDB Free, instance `nirikkha` (credentials outside repo).
- Vector DB: Supabase (project `nirikkha`, Free), Postgres 17.11 + pgvector 0.8.2. Data API OFF, automatic RLS ON. Session pooler (`SUPABASE_DB_URL`).
- Warehouse: DuckDB file `backend/.cache/analytics.duckdb` (git-ignored, rebuilt with `python -m app.analytics.warehouse --build`).
- Secrets: `backend/.env`, `frontend/.env.local` (git-ignored); passwords in `D:\AI_Buildfest\secrets\`.
- Design: "Evidence Room" (dark + light Paper mode), tokens in `docs/DESIGN.md`. Logo A.
- EDGAR: direct SEC API via httpx; User-Agent with name + email; <= 5 req/s; disk cache; `before=` cutoff.
- Parsing: BeautifulSoup + lxml, run LOCALLY. Sections -> paragraphs with page numbers from filer page breaks; never invented.
- Chunking: section-aware semantic chunking (bge-small topic shifts) + contextual headers; 600-3200 chars.
- Embeddings: LOCAL `BAAI/bge-small-en-v1.5` via fastembed (384 dims, $0, unlimited, private). Gemini embedding kept as option; measured free-tier limit = 1,000 embed requests/day/project.
- Retrieval: `app.rag.retrieve.retrieve()` = local query embedding -> hybrid (pgvector + full-text OR query, RRF, one SQL round trip, filters CIK / filed-before / forms) -> local cross-encoder rerank (ms-marco-MiniLM-L-6-v2) of top 20. Reused DB connection.
- Low rerank score (e.g. negative) = weak evidence -> will feed "Insufficient Evidence" in the Sentinel.
- Analytics (no AI): DuckDB YoY section size change (flag >= 25% on sections >= 2,000 chars) + term trends. Signals for review, never conclusions.

## Day 2 findings (review signals, not conclusions)
- SVB 10-K Item 7A (Market Risk) shrank 45.1% (14,505 -> 7,957 chars) from FY2021 to FY2022 filing. Only large-change flag for SVB.
- Apple: no large-change flags (shows the system does not flag everyone).
- SVB 10-K mentions: "held-to-maturity" 9 -> 5, "unrealized loss" 11 -> 13. "chief risk officer" appears only in proxies; latest proxy before cutoff = 2022-03-04.
- SVB 2022 proxy names a Chief Risk Officer (p.30). Post-mortems reportedly describe a CRO vacancy in 2022 -> MUST verify from reliable sources in Replay Step 1 before stating.

## Done
- [x] Day 1: accounts, repo + docs, backend live on Render, frontend live on Vercel, CORS, logo, design tokens
- [x] Day 2: EDGAR client, parser, semantic + contextual chunking, local embeddings, Supabase pgvector, hybrid search, reranker, DuckDB warehouse; 44 tests passing

## Data loaded
- SVB Financial Group (CIK 719739): 10-K 2022-03-01, 10-K 2023-02-24, DEF 14A 2021-03-04, DEF 14A 2022-03-04
- Apple Inc. (CIK 320193): 10-K 2024-11-01, 10-K 2025-10-31, DEF 14A 2025-01-10, DEF 14A 2026-01-08

## Next (Day 3)
- [ ] LLM client with fallback Groq -> Gemini -> local, token/latency/cost logging
- [ ] Neo4j relationship graph (directors, executives, committees, affiliations)
- [ ] Governance Rule Engine: Reg S-K Items 401, 402, 404, 407 with PASS / POTENTIAL_GAP / FAIL / INSUFFICIENT_EVIDENCE
- [ ] LangGraph agents for the 4 investigations

## Live links
- GitHub: https://github.com/ShArafat58/nirikkha
- Frontend: https://nirikkha.vercel.app
- Backend: https://nirikkha-api.onrender.com (/health, /docs)

## Score
- See `docs/SCORE_LEDGER.md`. Built: 53 / 425. Verified: 0 / 425.

## Known issues / risks
- Render auto-deploy does not trigger on push -> manual deploy; investigate GitHub App access before API work.
- Query embedding + reranker on Render need fastembed (512 MB RAM) -> test memory when the API is added; fallback: precomputed demo results.
- Local search latency 2-4 s (network distance BD -> Asia-Pacific); expected lower on Render.
- bge-small reads up to 512 tokens; tails of the longest chunks are not embedded (full text stored + keyword-searchable).
- Keyword counts can mislead (e.g. "no material weakness") -> findings must come from reading passages.
- Supabase Free pauses after 1 week of inactivity; Neo4j Aura Free deletes after 30 days of inactivity.
- Render free instance sleeps after ~15 min idle -> keep-warm ping + precomputed demo results.
- Parser: some proxy table rows / bio lines become small extra sections (text kept, labels noisy).
- Starlette TestClient deprecation warning (`httpx2`) -> harmless for now.
- Frontend: `npm audit` shows 5 high vulnerabilities -> do NOT `--force`; review before submission.
- Logo / favicon / README header built but not yet visually verified.
- Team: need 5th member and at least 1 NRB member.
- AI Detail Usage table in brief sums to 237 vs stated 232 - confirm on live form.