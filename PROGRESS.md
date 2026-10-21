# PROGRESS — Nirikkha

Updated: 22 Oct 2026, 00:10 (Asia/Dhaka). Submission target: 25 Oct 2026.

## Live

- App: https://nirikkha.vercel.app (Vercel, auto-deploy)
- API: https://nirikkha-api.onrender.com (Render, manual deploy after each push)
- Repo: https://github.com/ShArafat58/nirikkha

## Done

- Ingestion (10-K, DEF 14A, PRE 14A), semantic + contextual chunking, local embeddings, hybrid retrieval + RRF + rerank
- Neo4j relationship graph with quote-verified relations; DuckDB analytics
- LangGraph Crash-Test pipeline (13 nodes, 4 parallel investigations), rule engine (16 rules, N/A by sector), Reliability Sentinel, Health Score
- Legal memo (EN/BN), Reports, Graph, Replay, Radar (2 streams, Approve/Reject), Pricing, /docs, Admin (human review, users, jobs, public demos)
- SVB Replay published (VALID, 5/5 knowable signs raised, 0 missed), second run kept, Apple control
- 5 MCP servers built (stdio + HTTP), 5 community MCP servers used in Antigravity
- n8n: daily Radar scan → Telegram; Render warm-up
- Help chatbot (EN/BN, grounded, rate-limited, animated robot)
- Private mode with Ollama (fail-closed), measured on 8 GB CPU laptop
- Cloudflare tunnel for n8n and MCP
- Docs: README, ARCHITECTURE, DATA_LIFECYCLE, PROMPT_LIBRARY, ETHICS, REPLAY, LOCAL_MODELS, MCP, TUNNEL, EVALUATION, SCORE_LEDGER
- 234 backend tests passing

## Next

1. `docs/SUBMISSION.md`: pitch, summary, problem, solution, business model, market validation text
2. Security before submission: reset admin passwords, rotate Neo4j password, new AUTH_SECRET
3. Frontend AI builders (optional, 12 pts)
4. Pitch deck, 181-second video script, Figma link
5. End-to-end test, link checks, fill the form from SCORE_LEDGER

## Known issues

- Render free instance sleeps; warm-up only runs while n8n (Docker) is up
- Older cached reports predate the risk-committee N/A rule
- Quick-tunnel URLs change each run; some browsers flag trycloudflare.com
