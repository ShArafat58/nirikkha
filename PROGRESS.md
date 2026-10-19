# PROGRESS - Nirikkha

Last updated: 2026-10-20 03:50 (Day 2 - retrieval layer done)

## Decisions
- Product name: **Nirikkha** - tagline "Trust less, Verify more". Challenge: GovernanceIQ.
- Local path: `D:\AI_Buildfest\Nirikkha`
- GitHub: https://github.com/ShArafat58/nirikkha (public)
- Machine: Windows, 16 GB RAM, Intel UHD (no NVIDIA GPU) -> local models CPU-only; fine-tuning on Colab/Kaggle.
- Backend host: Render free web service (Python 3, root `backend`). Auto-deploy not triggering -> use Manual Deploy -> Deploy latest commit.
- Frontend: Next.js 16.4.2 + Tailwind + TypeScript on Vercel (root `frontend`), mock mode via `NEXT_PUBLIC_USE_MOCK`.
- Graph DB: Neo4j AuraDB Free, instance `nirikkha` (credentials outside repo).
- Vector DB: Supabase (org Nirikkha, project `nirikkha`, Free, nano), Postgres 17.11 + pgvector 0.8.2. Data API OFF, automatic RLS ON. Connection via Session pooler (`SUPABASE_DB_URL`).
- Secrets: `backend/.env`, `frontend/.env.local` (git-ignored); passwords in `D:\AI_Buildfest\secrets\`.
- Design: "Evidence Room" (dark + light Paper mode), tokens in `docs/DESIGN.md`. Logo A.
- EDGAR: direct SEC API via httpx; User-Agent with name + email; <= 5 req/s; disk cache; `before=` cutoff.
- Parsing: BeautifulSoup + lxml, run LOCALLY (Render has 512 MB). Sections -> paragraphs with page numbers from filer page breaks; never invented. TOC folded into `front_matter`.
- Chunking: section-aware semantic chunking (bge-small topic shifts) + contextual headers; size 600-3200 chars; numeric sections (Item 8, Item 15, front matter) split by size only.
- Embeddings: LOCAL `BAAI/bge-small-en-v1.5` via fastembed (384 dims, $0, unlimited, data stays on the machine). Gemini embedding code kept as an option; measured free-tier limit = 1,000 embed requests/day/project (each text counts).
- Retrieval: hybrid = pgvector cosine + Postgres full-text (OR query) fused with RRF (k=60); filters: CIK, filed-before date (Replay freeze also enforced in SQL), forms.
- SVB Replay facts: last 10-K filed 2023-02-24; latest proxy before the cutoff filed 2022-03-04.

## Done
- [x] Day 1: accounts, repo + docs, backend live on Render, frontend live on Vercel, CORS, logo, design tokens
- [x] Step 2.1 HEAD support on / and /health
- [x] Step 2.2 SEC EDGAR client (10-K + DEF 14A, cache, rate limit, cutoff)
- [x] Step 2.3 Parser (sections, pages, paragraphs, TOC folding)
- [x] Step 2.4 Semantic + contextual chunking (1,688 chunks from 8 filings)
- [x] Step 2.5 Embeddings (local, 517 s, $0) + Supabase pgvector + hybrid search; 38 tests passing

## Data loaded
- SVB Financial Group (CIK 719739): 10-K 2022-03-01, 10-K 2023-02-24, DEF 14A 2021-03-04, DEF 14A 2022-03-04
- Apple Inc. (CIK 320193): 10-K 2024-11-01, 10-K 2025-10-31, DEF 14A 2025-01-10, DEF 14A 2026-01-08

## Next (rest of Day 2)
- [ ] Step 2.6 Reranker
- [ ] Step 2.7 DuckDB analytics store
- [ ] Then Day 3: Neo4j graph, LangGraph agents (4 investigations), Rule Engine

## Live links
- GitHub: https://github.com/ShArafat58/nirikkha
- Frontend: https://nirikkha.vercel.app
- Backend: https://nirikkha-api.onrender.com (/health, /docs)

## Score
- See `docs/SCORE_LEDGER.md`. Built: 39 / 425. Verified: 0 / 425.

## Known issues / risks
- Render auto-deploy does not trigger on push -> manual deploy for now; investigate GitHub App access before API work.
- Query embedding on Render needs fastembed (512 MB RAM) -> test memory when the search API is added; fallback: precomputed query vectors for demo.
- bge-small reads up to 512 tokens; the tail of the longest chunks is not embedded (full text still stored and keyword-searchable).
- Supabase Free pauses after 1 week of inactivity -> run a query before demo and during judging.
- Neo4j Aura Free auto-deletes after 30 days of inactivity.
- Render free instance sleeps after ~15 min idle -> keep-warm ping + precomputed demo results.
- Parser: some proxy table rows / bio lines become small extra sections (text kept, labels noisy).
- Starlette TestClient deprecation warning (`httpx2`) -> harmless for now.
- Frontend: `npm audit` shows 5 high vulnerabilities -> do NOT `--force`; review before submission.
- Logo / favicon / README header built but not yet visually verified.
- Team: need 5th member and at least 1 NRB member.
- AI Detail Usage table in brief sums to 237 vs stated 232 - confirm on live form.