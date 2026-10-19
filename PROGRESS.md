# PROGRESS - Nirikkha

Last updated: 2026-10-20 00:55 (Day 1 infrastructure complete)

## Decisions
- Product name: **Nirikkha** - tagline "Trust less, Verify more". Challenge: GovernanceIQ.
- Local path: `D:\AI_Buildfest\Nirikkha`
- GitHub: https://github.com/ShArafat58/nirikkha (public)
- Machine: Windows, 16 GB RAM, Intel UHD (no NVIDIA GPU) -> local models CPU-only, small (1-4B); fine-tuning on Colab/Kaggle.
- Tools: Node v24.12.0, npm 11.6.2, Python 3.12.3, Git 2.43, Docker 29.1 / Compose v2.40.
- Backend host: Render free web service (Python 3, root `backend`). HF Docker Spaces now need a paid plan -> HF only for model hosting later.
- Backend also builds as a Docker image (`backend/Dockerfile`), verified locally.
- Frontend: Next.js 16.4.2 + Tailwind + TypeScript on Vercel (root `frontend`). Single project, not Vercel multi-service.
- Frontend reads backend URL from `NEXT_PUBLIC_API_URL`; `NEXT_PUBLIC_USE_MOCK=true` gives mock mode.
- CORS: backend `CORS_ORIGINS` = localhost:3000 + nirikkha.vercel.app. Vercel preview URLs are NOT allowed (use production URL for demos).
- Graph DB: Neo4j AuraDB Free, instance `nirikkha` (credentials outside repo in `D:\AI_Buildfest\secrets\`).
- Secrets: `backend/.env`, `frontend/.env.local` (both git-ignored); templates `.env.example`; production values in Render / Vercel settings.
- Gemini free tier may use inputs for product improvement -> only public filings go to Gemini; private docs to local models only.
- Render RAM 512 MB -> embeddings / reranking via free APIs.
- Owner builds the frontend for now; teammates may join later via `frontend/README.md`.

## Done
- [x] Step 1.1 Machine check
- [x] Step 1.2 Repo structure, .gitignore, README, first commit
- [x] Step 1.3 AGENTS.md + PROGRESS.md
- [x] Step 1.4 docs/SCORE_LEDGER.md
- [x] Step 1.5 docs/SPEC.md
- [x] Step 1.6 Neo4j Aura Free; Hugging Face account
- [x] Step 1.7 Groq + Gemini keys verified; env templates
- [x] Step 1.8 FastAPI skeleton + /health + 2 tests
- [x] Step 1.9 Docker image verified + backend live on Render (production)
- [x] Step 1.10 Next.js health page + mock mode + live on Vercel, CORS working, mobile OK

## Next
- [ ] Step 1.11 Design direction + logo
- [ ] Day 2: EDGAR fetch (10-K + DEF 14A), parsing with page/section, chunking, embeddings, pgvector, hybrid search, DuckDB

## Accounts
| Service | Status |
|---|---|
| GitHub | Yes |
| Groq | Yes (key verified) |
| Google AI Studio | Yes (key verified) |
| Supabase | Yes (not yet used) |
| Vercel | Yes (project `nirikkha`) |
| Render | Yes (service `nirikkha-api`) |
| Neo4j Aura | Yes (Free, `nirikkha`) |
| Hugging Face | Yes (token `nirikkha-deploy`) |

## Live links
- GitHub: https://github.com/ShArafat58/nirikkha
- Frontend: https://nirikkha.vercel.app
- Backend: https://nirikkha-api.onrender.com (/health, /docs)

## Score
- See `docs/SCORE_LEDGER.md`. Built: 7 / 425. Verified: 0 / 425.

## Known issues / risks
- Render free instance sleeps after ~15 min idle (~50 s cold start) -> keep-warm ping + precomputed demo results.
- Render free instance-hours shared across all free services in the account -> check / suspend unused ones.
- `HEAD /` returns 405 -> allow HEAD on `/` and `/health` in the next backend step.
- Starlette TestClient deprecation warning (`httpx2`) -> harmless for now.
- Frontend: `npm audit` shows 5 high vulnerabilities -> do NOT `--force`; review before submission.
- Team: need 5th member and at least 1 NRB member.
- AI Detail Usage table in brief sums to 237 vs stated 232 - confirm on live form.
- Neo4j Aura Free auto-deletes after 30 days of inactivity.