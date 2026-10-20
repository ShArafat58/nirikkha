# PROGRESS - Nirikkha

Last updated: 2026-10-20 20:35 (Days 1-4 COMPLETE on plan day 2 - two days ahead)

## Decisions
- Product: **Nirikkha** - "Trust less, Verify more". Challenge: GovernanceIQ (JusticeSphere AI). Also Risk Sentinel + Legal Copilot.
- Local: `D:\AI_Buildfest\Nirikkha` | GitHub: https://github.com/ShArafat58/nirikkha (public)
- Machine: Windows, 16 GB RAM, Intel UHD (CPU only). Fine-tuning later on Colab/Kaggle.
- Frontend: Next.js on Vercel. Backend: FastAPI on Render free (512 MB) - **queues only** (RUN_JOBS_INLINE=false).
- **Live analysis = job queue + worker**: Render stores the job in Postgres; `python -m app.api.worker` on the owner's
  laptop claims it (FOR UPDATE SKIP LOCKED), runs the full pipeline, writes per-node progress; Render serves polling.
  Worker heartbeat in `workers` table; GET /api/status shows worker_online. No worker within 5 min -> job fails with
  a clear message; cached demos always open. Inline mode also claims atomically (no double runs).
- Render RAM tests: full pipeline peaked > 512 MB twice (2 ONNX models) -> instance restarted; worker mode keeps Render at ~113 MB.
- Data: Supabase Postgres 17 + pgvector (filings, chunks, crash_tests, workers), Neo4j Aura (governance graph),
  DuckDB warehouse (snapshot committed at backend/data/analytics.duckdb; resolve_db: .cache first, then data/).
- Retrieval: hybrid (pgvector + full-text, RRF) -> local cross-encoder rerank. Settings RERANK_ENABLED, RERANK_CANDIDATES, ONNX_THREADS.
- LLM router: extract = qwen3.8-27b; plan = gpt-oss-20b; guard = gpt-oss-safeguard-20b; analyst = gemini-2.5-flash;
  Sentinel judge + legal memo = gpt-oss-120b. Cache, usage log, per-model budgets, retry-after.
- Crash-Test graph: redact -> guard -> collect -> plan -> gather -> analyze -> 4 investigations -> merge -> sentinel -> score
  (+ report sections). Severity and confidence separate; insufficient evidence listed, never scored as low risk.
- Health Score: 100 - sum over investigations of min(30, severity x confidence); coverage % separate; warnings.
- Legal memo: 3-5 non-obvious risks, >= 2 finding ids each, rules only from evaluated Reg S-K list with exact meanings;
  intent words dropped; absence and conduct wording flagged for legal review.
- Prompts versioned in app/prompts (extract v1/v2, guard v1, plan v1/v2, analyze v1/v2, sentinel_judge v1, legal_memo v1-v3).

## Results (SVB, evidence frozen 2023-03-10) - review signals, not conclusions
- Deposit-partnership decision: 18 findings, Sentinel 12 verified / 4 needs review / 2 downgraded, Health 52/100 elevated_concern
  (an earlier run scored 42; judge verdicts vary between live runs - the stored run is the frozen demo).
- Credit-line decision via Render + worker: Health 57/100. Custody-account decision: 55/100.
- Item 7A shrank 45.1%; CEO is a Class A director of the Federal Reserve Bank of San Francisco; related-party items
  BlackRock ~$30.0M, Cachematrix ~$706,674, Vanguard ~$322,391; proxy facts 371 days old.
- CRO vacancy (post-mortems) must be verified from reliable sources in Replay Step 1 before stating.

## Evaluation (python -m evaluation.run, docs/EVALUATION.md)
- Retrieval, 10 gold questions: rerank top-20 hit@1 90% / hit@3 100% / MRR 0.933; rerank top-10 80% / 100% / 0.883;
  hybrid only 50% / 70% / 0.567.
- Injection heuristic 6/6 (optimistic: attacks written knowing the patterns), 0/6 false positives; PII 8/8, 0/6 altered.
- Rule regression OK (11 PASS, 3 POTENTIAL_GAP); memo citation pass rate 1.0. Extraction quote verification 137/162 (85%).

## Done
- [x] Day 1: accounts, repo + docs, live backend + frontend, CORS, logo, design tokens
- [x] Day 2: EDGAR, parser, chunking, local embeddings, pgvector, hybrid search, reranker, DuckDB
- [x] Day 3: LLM router, governance extraction + Neo4j, Rule Engine, LangGraph Crash-Test with analyst
- [x] Day 4: Reliability Sentinel, Health Score, report sections, legal memo, PII guardrail, evaluation suite,
      REST API (crash-tests, memo, companies, evaluation, status) + docs/API.md, job queue + worker; 142 tests

## How to run a live analysis
1. Laptop: `cd backend; .\.venv\Scripts\Activate.ps1; python -m app.api.worker` (keep the window open)
2. Anyone: frontend or POST https://nirikkha-api.onrender.com/api/crash-tests -> poll GET /api/crash-tests/{id}
3. Render does not auto-deploy: after every push use Manual Deploy -> Deploy latest commit.

## Next (Day 5): frontend
- [ ] Design direction agreed with owner (section 11), palette, fonts (incl. Bengali), page list
- [ ] Pages: company + decision input, live progress, Crash-Test report (severity vs confidence), evidence panel,
      Rule Engine, Health Score explanation, relationship graph, memo, pricing, /docs; Bengali toggle; mock mode
- [ ] Frontend AI builders used for real UI parts (ledger A20)
- Later: Apple 2026 proxy extraction; SVB Replay; Radar + Approve/Reject; n8n; MCP servers; Ollama private mode; LoRA

## Live links
- Frontend: https://nirikkha.vercel.app | Backend: https://nirikkha-api.onrender.com (/health, /docs, /api/status)

## Score
- See `docs/SCORE_LEDGER.md`. Built: 104 / 425. Verified: 0 / 425.

## Known issues / risks
- Live analysis needs the laptop worker running; otherwise only cached demos (by design, stated in the UI).
- Render auto-deploy not triggering (manual deploy). Free instance sleeps; first request ~50 s.
- Groq daily token caps -> precompute; Gemini flash limits not measured.
- Supabase Free pauses after 1 week idle; Neo4j Aura Free deletes after 30 days idle.
- Windows PowerShell 5.1 shows UTF-8 punctuation as mojibake in console output (display only).
- PowerShell variables are case-insensitive ($r == $R): use $root for the project folder.
- Team: 5th + NRB member handled by a teammate. AI Detail table sums 237 vs stated 232 - confirm on live form.