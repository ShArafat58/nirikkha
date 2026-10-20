# PROGRESS - Nirikkha

Last updated: 2026-10-20 14:20 (Day 3 in progress)

## Decisions
- Product name: **Nirikkha** - tagline "Trust less, Verify more". Challenge: GovernanceIQ.
- Local path: `D:\AI_Buildfest\Nirikkha` | GitHub: https://github.com/ShArafat58/nirikkha (public)
- Machine: Windows, 16 GB RAM, Intel UHD (no NVIDIA GPU) -> local models CPU-only; fine-tuning on Colab/Kaggle.
- Backend: Render free (Python 3, root `backend`), manual deploy. Frontend: Next.js 16.4.2 + Tailwind on Vercel.
- Data stores: Supabase Postgres 17 + pgvector (chunks), DuckDB (analytics), Neo4j Aura Free (governance graph).
- Secrets: `backend/.env`, `frontend/.env.local` (git-ignored); passwords in `D:\AI_Buildfest\secrets\`.
- Design: "Evidence Room", tokens in `docs/DESIGN.md`. Logo A.
- Ingestion (local / precomputed): EDGAR API -> BeautifulSoup parser (sections, pages from filer page breaks) -> semantic + contextual chunks -> local bge-small embeddings -> Supabase.
- Retrieval: hybrid (pgvector + full-text, RRF, one SQL round trip) -> local cross-encoder rerank.
- LLM router `app/llm/client.py`, tasks and routes:
  reason = gpt-oss-120b -> gemini-2.5-flash -> local; fast = gpt-oss-20b -> gemini-2.5-flash-lite -> local;
  extract = qwen3.8-27b -> gpt-oss-20b -> gemini-2.5-flash -> local; safety = gpt-oss-safeguard-20b -> gpt-oss-20b;
  bangla = gemini-2.5-flash -> qwen3.8-27b. Response cache, usage log (.cache/llm_usage.jsonl), per-model budgets.
- Groq free-tier limits measured 2026-10-20: gpt-oss-120b / gpt-oss-20b / qwen3.8-27b = 30 RPM, 1K RPD, 8K TPM, 200K TPD;
  gpt-oss-safeguard-20b = 3 RPM, 2K TPM. Gemini limits for our models not visible -> assumed conservative.
- Budget logic: minute window counts reserved tokens (prompt + max output); daily totals from usage log; on 429 "try again in Xs" wait and retry once; batch jobs use max_wait=75 s.
- Extraction: prompt `app/prompts/extract_governance.v2.md` (v1 kept); governance sections only; previous chunk tail as PRECEDING CONTEXT for split tables; every relation needs a verbatim quote; unverified relations never enter the graph.
- Entity resolution: person key = first + last name, bare surname -> unique full name, multi-person phrases skipped; org key ignores suffixes; table-derived evidence flagged `from_table` (lower confidence later).
- Graph model: (Person)-[DIRECTOR_OF|OFFICER_OF|CHAIRS_BOARD]->(Company); (Person)-[MEMBER_OF {chair}]->(Committee)-[COMMITTEE_OF]->(Company); (Person)-[BOARD_SEAT|EMPLOYED_BY]->(Organization); (Party)-[RELATED_TRANSACTION]->(Company); evidence (accession, chunk, page, quote) on every edge.
- Extraction of one proxy takes ~30 min on the free tier -> demo companies are precomputed; live new companies would run in background.

## Findings so far (review signals, never conclusions)
- SVB 10-K Item 7A shrank 45.1% FY2021 -> FY2022 filing; Apple has no large-change flags.
- SVB 2022 proxy: CEO Greg Becker holds a board seat at the Federal Reserve Bank of San Francisco (p.10) -> potential conflict, review.
- Shared prior employer: director Kate Mitchell and CRO Laura Izurieta (Bank of America).
- Related-party items (p.25): BlackRock ~$30.0 million fee sharing revenue, Cachematrix ~$706,674 fees paid, Vanguard ~$322,391.
- Audit Committee shows two chairs from table rows -> table-derived evidence needs human review.
- No verified "board chair" quote extracted -> board leadership = insufficient evidence from extraction alone.
- CRO vacancy in 2022 (reported in post-mortems) MUST be verified from reliable sources in Replay Step 1 before stating.

## Done
- [x] Day 1: accounts, repo + docs, live backend + frontend, CORS, logo, design tokens
- [x] Day 2: EDGAR, parser, chunking, local embeddings, pgvector, hybrid search, reranker, DuckDB
- [x] Step 3.1 LLM router with fallback, cache, usage log; Step 3.2a per-model rate-limit budgets
- [x] Step 3.2b governance extraction (SVB 2022 proxy: 162 relations, 137 verified, 0 failed, 147K tokens, $0)
- [x] Step 3.2c Neo4j graph + entity resolution + governance report queries; 67 tests passing

## Next (Day 3)
- [ ] Governance Rule Engine: Reg S-K Items 401, 402, 404, 407 -> PASS / POTENTIAL_GAP / FAIL / INSUFFICIENT_EVIDENCE
- [ ] LangGraph agents for the 4 investigations (decision-focused)
- [ ] Extract + load Apple 2026 proxy (needs fresh daily token budget) and SVB 2021 proxy (for year-over-year board changes)

## Live links
- Frontend: https://nirikkha.vercel.app | Backend: https://nirikkha-api.onrender.com (/health, /docs)

## Score
- See `docs/SCORE_LEDGER.md`. Built: 74 / 425. Verified: 0 / 425.

## Known issues / risks
- Groq daily token caps (200K per model) limit extraction to ~1 proxy per model per day -> precompute, cache.
- Render auto-deploy does not trigger -> manual deploy; query embedding + reranker on Render need RAM test.
- Local search latency 2-4 s (network distance); expected lower on Render.
- Supabase Free pauses after 1 week idle; Neo4j Aura Free deletes after 30 days idle.
- Parser / extraction label noise: committee name variants (e.g. "Compensation Committee" vs "Compensation & Human Capital Committee").
- Starlette TestClient deprecation warning; frontend npm audit (5 high) to review; logo visuals not yet verified.
- Team: 5th member + NRB member handled by a teammate.
- AI Detail Usage table in brief sums to 237 vs stated 232 - confirm on live form.