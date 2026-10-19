# PROGRESS - Nirikkha

Last updated: 2026-10-20 02:10 (Day 2 in progress)

## Decisions
- Product name: **Nirikkha** - tagline "Trust less, Verify more". Challenge: GovernanceIQ.
- Local path: `D:\AI_Buildfest\Nirikkha`
- GitHub: https://github.com/ShArafat58/nirikkha (public)
- Machine: Windows, 16 GB RAM, Intel UHD (no NVIDIA GPU) -> local models CPU-only, small (1-4B); fine-tuning on Colab/Kaggle.
- Tools: Node v24.12.0, npm 11.6.2, Python 3.12.3, Git 2.43, Docker 29.1 / Compose v2.40.
- Backend host: Render free web service (Python 3, root `backend`). HF Docker Spaces need a paid plan -> HF only for model hosting later.
- Frontend: Next.js 16.4.2 + Tailwind + TypeScript on Vercel (root `frontend`), mock mode via `NEXT_PUBLIC_USE_MOCK`.
- CORS: `CORS_ORIGINS` = localhost:3000 + nirikkha.vercel.app.
- Graph DB: Neo4j AuraDB Free, instance `nirikkha` (credentials outside repo).
- Secrets: `backend/.env`, `frontend/.env.local` (git-ignored); production values in Render / Vercel.
- Gemini free tier may use inputs -> only public filings go to Gemini; private docs to local models only.
- Design: "Evidence Room" (dark + light Paper mode), tokens in `docs/DESIGN.md`. Logo A.
- EDGAR: direct SEC API (`data.sec.gov` + Archives) via httpx; User-Agent with name + email; <= 5 req/s; disk cache; `before=` cutoff freezes evidence for the Replay.
- Parsing: BeautifulSoup + lxml, run LOCALLY / precomputed (SVB 10-K is ~9.8M chars; Render has 512 MB). Output: sections -> paragraphs with page numbers from the filer's page breaks; page = None if no markers (never invented). TOC folded into `front_matter`.
- SVB Replay facts found: last 10-K filed 2023-02-24 (14 days before failure); latest proxy available before the cutoff was filed 2022-03-04 (no 2023 proxy before failure).

## Done
- [x] Day 1 (Steps 1.1 - 1.11): accounts, repo + docs, backend live on Render, frontend live on Vercel, CORS, logo, favicon, design tokens
- [x] Step 2.1 HEAD support on / and /health (live HEAD = 200)
- [x] Step 2.2 SEC EDGAR client: 10-K + DEF 14A, cache, rate limit, cutoff (Apple + SVB verified)
- [x] Step 2.3 Parser: sections + pages + paragraphs, TOC folding (SVB 10-K: 181 pages, 23 sections)

## Next (Day 2)
- [ ] Step 2.4 Chunking (semantic + contextual) + embeddings
- [ ] pgvector on Supabase
- [ ] Hybrid search + reranker
- [ ] DuckDB analytics store

## Live links
- GitHub: https://github.com/ShArafat58/nirikkha
- Frontend: https://nirikkha.vercel.app
- Backend: https://nirikkha-api.onrender.com (/health, /docs)

## Score
- See `docs/SCORE_LEDGER.md`. Built: 11 / 425. Verified: 0 / 425.

## Known issues / risks
- Render auto-deploy: setting saved as "On Commit"; not yet confirmed that a push triggers a deploy.
- Render free instance sleeps after ~15 min idle (~50 s cold start) -> keep-warm ping + precomputed demo results.
- Render free instance-hours shared across all free services in the account.
- Parser: proxy table rows starting with a heading keyword can become headings (e.g. Apple "Summary Compensation Table (SCT) Total 74,294,811") -> reject lines with thousand-separated numbers.
- Parser: committee names inside director bios create small extra proxy sections (text kept, only labels noisy).
- Starlette TestClient deprecation warning (`httpx2`) -> harmless for now.
- Frontend: `npm audit` shows 5 high vulnerabilities -> do NOT `--force`; review before submission.
- Logo / favicon / README header built but not yet visually verified.
- Team: need 5th member and at least 1 NRB member.
- AI Detail Usage table in brief sums to 237 vs stated 232 - confirm on live form.
- Neo4j Aura Free auto-deletes after 30 days of inactivity.