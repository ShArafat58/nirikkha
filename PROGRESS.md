# PROGRESS — Nirikkha

Last updated: 2026-10-19 (Day 1)

## Decisions

- Product name: **Nirikkha (নিরীক্ষা)** — tagline "Trust less, Verify more". Challenge: GovernanceIQ.
- Local path: `D:\AI_Buildfest\Nirikkha`
- GitHub: https://github.com/ShArafat58/nirikkha (public)
- Machine: Windows, 16 GB RAM, Intel UHD (no NVIDIA GPU) -> local models CPU-only, small (1-4B); fine-tuning on Colab/Kaggle.
- Tools: Node v24.12.0, npm 11.6.2, Python 3.12.3, Git 2.43, Docker 29.1 / Compose v2.40.
- Backend host: Hugging Face Spaces (Docker) primary, Render backup.
- Graph DB: Neo4j AuraDB Free, instance `nirikkha` (credentials stored outside repo in `D:\AI_Buildfest\secrets\`).
- Secrets: `backend/.env` (git-ignored); template in `backend/.env.example`.
- Gemini free tier may use inputs for product improvement -> only public filings go to Gemini; private docs go to local models only.
- Logo: to be designed at end of Day 1 (SVG, then imported into Figma).

## Done

- [x] Step 1.1 Machine check
- [x] Step 1.2 Repo structure, .gitignore, README, first commit, pushed to GitHub
- [x] Step 1.3 AGENTS.md + PROGRESS.md
- [x] Step 1.4 docs/SCORE_LEDGER.md
- [x] Step 1.5 docs/SPEC.md
- [x] Step 1.6 Neo4j Aura Free instance running; Hugging Face account verified

## In progress

- [ ] Step 1.7 Groq + Gemini API keys, backend/.env + .env.example

## Next

- [ ] Step 1.8 FastAPI skeleton + /health (local)
- [ ] Deploy backend to Hugging Face Spaces
- [ ] Next.js page live on Vercel
- [ ] Design direction + logo

## Accounts

| Service          | Status                 |
| ---------------- | ---------------------- |
| GitHub           | Yes                    |
| Groq             | Yes                    |
| Supabase         | Yes                    |
| Google AI Studio | Yes                    |
| Vercel           | Yes                    |
| Render           | Yes                    |
| Neo4j Aura       | Yes (Free, `nirikkha`) |
| Hugging Face     | Yes (email verified)   |

## Live links

- GitHub: https://github.com/ShArafat58/nirikkha
- Frontend: —
- Backend: —

## Score

- See `docs/SCORE_LEDGER.md`. Built: 5 / 425. Verified: 0 / 425.

## Known issues / risks

- Day 1 targets (/health live, Next.js live) spill into 20 Oct morning.
- Team: need 5th member and at least 1 NRB member.
- Score table in the brief sums to 237 for AI Detail Usage vs stated 232 — confirm against the live form.
- Neo4j Aura Free auto-deletes after 30 days of inactivity — run a query periodically after submission.
