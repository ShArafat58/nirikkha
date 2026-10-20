# PROGRESS - Nirikkha

Last updated: 2026-10-20 15:35 (Day 4 in progress - one day ahead of plan)

## Decisions
- Product name: **Nirikkha** - tagline "Trust less, Verify more". Challenge: GovernanceIQ.
- Local path: `D:\AI_Buildfest\Nirikkha` | GitHub: https://github.com/ShArafat58/nirikkha (public)
- Machine: Windows, 16 GB RAM, Intel UHD (no NVIDIA GPU) -> local models CPU-only; fine-tuning on Colab/Kaggle.
- Backend: Render free (Python 3, root `backend`), manual deploy. Frontend: Next.js 16.4.2 + Tailwind on Vercel.
- Data stores: Supabase Postgres 17 + pgvector (chunks), DuckDB (analytics), Neo4j Aura Free (governance graph).
- Ingestion (local / precomputed): EDGAR API -> BeautifulSoup parser -> semantic + contextual chunks -> local bge-small embeddings -> Supabase.
- Retrieval: hybrid (pgvector + full-text, RRF, one SQL round trip) -> local cross-encoder rerank.
- LLM router `app/llm/client.py`, tasks: reason = gpt-oss-120b; fast = gpt-oss-20b; extract = qwen3.8-27b;
  safety = gpt-oss-safeguard-20b; analyze = gemini-2.5-flash -> gpt-oss-120b; bangla = gemini-2.5-flash.
  Cache, usage log, per-model RPM/TPM/TPD budgets, retry-after on 429. Groq free tier: 8K TPM / 200K TPD per model.
- Extraction: prompt extract_governance.v2 with quote verification; table evidence flagged; unverified never enters the graph.
- Graph: Person / Company / Committee / Organization / Party / Filing; evidence (accession, chunk, page, quote) on every edge.
- Rule Engine `app/rules/engine.py`: 15 rules (Reg S-K 401(a), 401(e)(2), 402(c), 402(v), 404(a), 404(b), 407(a), 407(d)(5), 407(h);
  2 best practice; 4 internal indicators). Deterministic; categories never mixed; PVP not applicable before FY ending 2022-12-16;
  evidence = one sentence that matches the rule pattern (abbreviations like "Mr." allowed); phrase search + retrieval.
- Crash-Test (LangGraph) `app/agents/graph.py`: guard -> collect -> plan -> gather -> analyze -> [relationship | consistency |
  regulatory | missing_evidence] -> merge. Findings keep risk_severity and evidence_confidence separate; analyst answers only from
  an evidence pack (E# passages, G# graph facts, R# rule results); answers without valid citations become "insufficient".
- Prompts (versioned, all in `app/prompts/`): extract_governance v1/v2, guard_input v1, plan_decision v1/v2, analyze_questions v1/v2.

## SVB Crash-Test as of 2023-03-10 (deposit-partnership decision) - review signals, not conclusions
- 18 findings: 3 high, 10 medium, 5 low; 11 deterministic, 7 analyst (LLM); 3 LLM calls, ~8.6K tokens, $0.
- CON: Item 7A (Market Risk) shrank 45.1% FY2021 -> FY2022 filing (high severity, medium confidence).
- REL: CEO Greg Becker is a Class A director of the Federal Reserve Bank of San Francisco (high severity, high confidence).
- REL: related-party items BlackRock ~$30.0M fee-sharing revenue, Cachematrix ~$706,674, Vanguard ~$322,391.
- MIS: board and officer facts are from the 2022-03-04 proxy (371 days old) -> check Form 8-K Item 5.02.
- Known analyst errors kept as Sentinel test cases: absence claims ("do not disclose" liquidity metrics, independent audit),
  citing the 2021 proxy when the 2022 proxy is latest.
- Rule Engine: 11 PASS, 3 POTENTIAL_GAP, PVP not applicable. Apple (today): extraction not run -> 6 rules INSUFFICIENT_EVIDENCE (no guessing).
- CRO vacancy in 2022 (reported in post-mortems) MUST be verified from reliable sources in Replay Step 1 before stating.

## Done
- [x] Day 1: accounts, repo + docs, live backend + frontend, CORS, logo, design tokens
- [x] Day 2: EDGAR, parser, chunking, local embeddings, pgvector, hybrid search, reranker, DuckDB
- [x] Day 3: LLM router + budgets, governance extraction + Neo4j graph, Rule Engine, LangGraph Crash-Test with analyst; 90 tests
- [x] Step 4.1: AI Reliability Sentinel (sentinel.py, judge gpt-oss-120b in batches of 4, node merge -> sentinel). SVB: 12 verified, 6 human review, 0 judge errors; 98 tests
- [x] Step 4.2: Explainable Health Score (score.py, node sentinel -> score). SVB as of 2023-03-10: 42/100 elevated_concern, coverage 86%, 2 insufficient, 6 human review, relationship capped at 30; 105 tests
- [x] Step 4.3a: Crash-Test Report sections (report.py): 4 sections, EDGAR source links, rules law -> best practice -> internal, de-duplicated actions, human review first; 109 tests
- [x] Step 4.3b: Legal memo (memo.py, prompt legal_memo.v3, gpt-oss-120b). Code verifies: >=2 known finding ids per risk, rules only from the evaluated Reg S-K list with exact meanings, intent words dropped, absence and conduct-wording flagged for legal review, evidence gaps + disclaimer by code. SVB: complete, 4 risks; 118 tests
- [x] Step 4.4a: PII redaction guardrail (app/guardrails/pii.py, graph node redact before guard): email, phone, SSN, card (Luhn), IBAN, IP; accession, CIK and dates protected; only counts stored; 122 tests
- [x] Step 4.4b: Evaluation suite (python -m evaluation.run -> docs/EVALUATION.md): retrieval hit@1 90%, hit@3 100%, MRR 0.933; injection 6/6 (optimistic), PII 8/8 with 0/6 false positives; rule regression OK

## Next (Day 4)
- [ ] Reliability Sentinel (LLM-as-judge with a different model + deterministic checks: citation supports claim, contradictions,
      authoritative source, correct reporting period, enough evidence, human review)
- [ ] Explainable Governance Health Score (formula to agree with owner; severity and confidence separate; insufficient evidence visible)
- [ ] Crash-Test Report (4 sections) + Legal memo (>= 3 non-obvious risks, verified citations, gpt-oss-120b)
- [ ] PII redaction guardrail; evaluation set
- [ ] FastAPI endpoints + Render memory test
- [ ] Extract + load Apple 2026 proxy (fresh daily token budget)

## Live links
- Frontend: https://nirikkha.vercel.app | Backend: https://nirikkha-api.onrender.com (/health, /docs)

## Score
- See `docs/SCORE_LEDGER.md`. Built: 104 / 425. Verified: 0 / 425.

## Known issues / risks
- Crash-Test takes ~2.5 min locally (14 retrievals over BD -> Asia-Pacific network) -> precompute demo companies; measure on Render.
- Groq daily token caps (200K per model) limit extraction to ~1 proxy per model per day -> precompute, cache.
- Gemini free-tier limits for gemini-2.5-flash not measured -> watch for 429; analyst falls back to gpt-oss-120b with a compact pack.
- Render auto-deploy does not trigger -> manual deploy; query embedding + reranker on Render need RAM test.
- Supabase Free pauses after 1 week idle; Neo4j Aura Free deletes after 30 days idle.
- Committee name variants and two-chair table reading (flagged as low-confidence consistency finding).
- Frontend npm audit (5 high) to review; logo visuals not yet verified. Team: 5th + NRB member handled by a teammate.
- AI Detail Usage table in brief sums to 237 vs stated 232 - confirm on live form.