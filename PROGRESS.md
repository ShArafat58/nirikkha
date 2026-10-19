# PROGRESS - Nirikkha

Last updated: 2026-10-20 00:10 (end of Day 1 session)

## Decisions
- Product name: **Nirikkha** - tagline "Trust less, Verify more". Challenge: GovernanceIQ.
- Local path: `D:\AI_Buildfest\Nirikkha`
- GitHub: https://github.com/ShArafat58/nirikkha (public)
- Machine: Windows, 16 GB RAM, Intel UHD (no NVIDIA GPU) -> local models CPU-only, small (1-4B); fine-tuning on Colab/Kaggle.
- Tools: Node v24.12.0, npm 11.6.2, Python 3.12.3, Git 2.43, Docker 29.1 / Compose v2.40.
- Backend host: **Render free web service (Python 3, root `backend`)**. Hugging Face Docker Spaces now require a paid plan, so HF is used only for model hosting / model card later.
- Backend also builds and runs as a Docker image (`backend/Dockerfile`), verified locally on port 7860.
- Graph DB: Neo4j AuraDB Free, instance `nirikkha` (credentials outside repo in `D:\AI_Buildfest\secrets\`).
- Secrets: `backend/.env` (git-ignored); template `backend/.env.example`; production values in Render Environment.
- Gemini free tier may use inputs for product improvement -> only public filings go to Gemini; private docs go to local models only.
- Low RAM on Render (512 MB) -> embeddings / reranking via free APIs, not loaded in the server.
- Logo: to be designed with the design direction (SVG, then Figma).

## Done
- [x] Step 1.1 Machine check
- [x] Step 1.2 Repo structure, .gitignore, README, first commit, pushed
- [x] Step 1.3 AGENTS.md + PROGRESS.md
- [x] Step 1.4 docs/SCORE_LEDGER.md
- [x] Step 1.5 docs/SPEC.md
- [x] Step 1.6 Neo4j Aura Free running; Hugging Face account verified
- [x] Step 1.7 Groq + Gemini keys verified; backend/.env + .env.example
- [x] Step 1.8 FastAPI skeleton + /health + 2 pytest tests passing
- [x] Step 1.9 Dockerfile (local container verified) + backend live on Render (env=production)

## In progress
- [ ] Step 1.10 Next.js page live on Vercel

## Next
- [ ] Design direction + logo
- [ ] Day 2: EDGAR fetch (10-K + DEF 14A), parsing, chunking, embeddings, pgvector, hybrid search, DuckDB

## Accounts
| Service | Status |
|---|---|
| GitHub | Yes |
| Groq | Yes (key verified) |
| Google AI Studio | Yes (key verified) |
| Supabase | Yes |
| Vercel | Yes |
| Render | Yes (service `nirikkha-api`) |
| Neo4j Aura | Yes (Free, `nirikkha`) |
| Hugging Face | Yes (email verified, token `nirikkha-deploy`) |

## Live links
- GitHub: https://github.com/ShArafat58/nirikkha
- Backend: https://nirikkha-api.onrender.com (health: /health, docs: /docs)
- Frontend: -

## Score
- See `docs/SCORE_LEDGER.md`. Built: 5 / 425. Verified: 0 / 425.

## Known issues / risks
- Render free instance sleeps after ~15 min idle (~50 s cold start) -> add keep-warm ping + precomputed demo results.
- Render free instance-hours are shared across all free services in the account (6 other services exist) -> check / suspend unused ones.
- `HEAD /` returns 405 -> allow HEAD on `/` and `/health` in the next backend step.
- Starlette TestClient deprecation warning (suggests `httpx2`) -> harmless for now; revisit if tests break.
- Team: need 5th member and at least 1 NRB member.
- Score table in the brief sums to 237 for AI Detail Usage vs stated 232 - confirm against the live form.
- Neo4j Aura Free auto-deletes after 30 days of inactivity - run a query periodically after submission.