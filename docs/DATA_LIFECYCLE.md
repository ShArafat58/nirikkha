# Data lifecycle

How data enters Nirikkha, how it is cleaned and stored, how insights reach people, and how quality,
privacy, lineage and cost are controlled. Everything here is implemented in this repository.

## 1. Sources

| Source                   | Type                            | What we take                                                                                                                      | How                                                                                           |
| ------------------------ | ------------------------------- | --------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------- |
| SEC EDGAR                | External API / public open data | Form 10-K, DEF 14A, PRE 14A filings; company submissions (SIC code, filing list)                                                  | `data.sec.gov` JSON and filing archives, User-Agent with contact, paced requests, local cache |
| Curated SEC rule changes | Curated public sources          | 4 rule changes (pay versus performance, clawback, Rule 10b5-1, cybersecurity disclosure) with dates, affected items, Bengali text | `backend/data/radar/regulatory_updates.json`                                                  |
| Replay case file         | Curated public records          | SVB timeline (12 events, 6 warning signs) with event date and public date for each item                                           | `backend/data/replay/svb/case.json`                                                           |
| LLM providers            | External APIs                   | Model outputs only (no training data)                                                                                             | Groq, Google AI Studio (Gemini) free tiers; local Ollama in Private mode                      |
| User input               | User text                       | Company, decision text, freeze date; chatbot questions                                                                            | Web UI → REST API, PII-redacted before any model sees it                                      |
| Synthetic data           | Synthetic                       | PII and prompt-injection test sets, fake models in tests                                                                          | `backend/tests/`, `backend/evaluation/`                                                       |

No real personal data beyond what companies publish about their directors and officers in SEC filings.

## 2. Acquisition and extraction

| Method                                                                             | Where                                 |
| ---------------------------------------------------------------------------------- | ------------------------------------- |
| API pull from SEC EDGAR (submissions JSON, filing index, documents)                | `app/ingest/edgar.py`                 |
| Single-filing ingestion of a specific form end to end                              | `app/ingest/single.py`                |
| AI extraction of governance relations with quote verification                      | `app/graph/extract.py`                |
| MCP data access: `list_sec_filings` and graph tools for agents and IDE hosts       | `mcp-servers/`                        |
| Scheduled pulls: n8n runs the Radar scan daily, which checks EDGAR for new filings | `workflows/radar-daily-telegram.json` |

## 3. Parsing, cleaning, formatting, schema

| Stage             | What it does                                                                                                                                                                                                                                  |
| ----------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Parsing           | BeautifulSoup + lxml turn filing HTML into sections and paragraphs with page numbers; the form type is read back from the parsed cache so citations show the right form                                                                       |
| Cleaning          | Whitespace and boilerplate normalisation, table-aware handling (numeric tables split by size), name merging (Tom → Thomas), committee name normalisation ("Comp/HC" → "compensation and human capital"), table rows must name their committee |
| De-duplication    | SHA-256 content hash per chunk; embedding cache keyed by hash; analysis cache keyed by company + date + decision hash                                                                                                                         |
| Formatting        | Contextual header on every chunk (company, form, date, section, pages); reports rendered as JSON for the API and as Markdown for memos                                                                                                        |
| Schema validation | Pydantic models for every API request and response, LLM JSON outputs and rule results; invalid model JSON triggers a retry or the next model                                                                                                  |

## 4. Storage

| Store                  | Holds                                                                                                                 |
| ---------------------- | --------------------------------------------------------------------------------------------------------------------- |
| Supabase Postgres      | Filings, chunks, crash-test jobs and reports, users, Radar alerts and decisions, memos                                |
| pgvector (in Postgres) | 384-dimension chunk embeddings for semantic search                                                                    |
| Postgres full-text     | Keyword search over the same chunks                                                                                   |
| Neo4j Aura             | Person, Company, Committee, Organization nodes and their relations, each with its source quote                        |
| DuckDB                 | `backend/data/analytics.duckdb` snapshot for cross-company and cross-year analytics                                   |
| Local files            | Raw and parsed filing cache, embedding cache, extraction cache, `llm_usage.jsonl` usage log, published Replay results |

Formats: HTML (filings), JSON (EDGAR API, reports, cases, workflows), Markdown (memos, prompts), PDF (memo export through print).

## 5. Analytics and ML

| Method                 | Use                                                                                         |
| ---------------------- | ------------------------------------------------------------------------------------------- |
| LLM + RAG              | Planning, evidence answers, extraction, Sentinel judging, memos                             |
| Rule engine (no AI)    | 16 Regulation S-K and best-practice rules with deterministic results                        |
| Embeddings             | `bge-small-en-v1.5` for semantic chunking and retrieval                                     |
| Cross-encoder ranking  | `ms-marco-MiniLM-L-6-v2` reranks candidates                                                 |
| Statistical / analytic | Year-over-year disclosure change checks, coverage and score arithmetic, DuckDB aggregations |
| Graph analytics        | Interlocks and shared outside organisations in Neo4j                                        |

## 6. Orchestration, scheduling, streaming

- **Orchestration:** LangGraph runs the 13-node Crash-Test pipeline with the four investigations in parallel. A Postgres job queue separates the API from the worker. n8n orchestrates scheduled jobs.
- **Scheduling:** n8n runs the Radar scan every day at 09:00 Asia/Dhaka and pings the backend every 10 minutes to keep the free instance awake.
- **Streaming:** each pipeline node writes a progress event (stage, message, duration) to the job; the UI shows them live with an elapsed timer.

## 7. Delivery of insights

| Channel            | What the user gets                                                                                                                  |
| ------------------ | ----------------------------------------------------------------------------------------------------------------------------------- |
| Web app            | Crash-Test report, Health Score explanation, evidence panel with the exact passage, rule results, relationship graph, Replay, Radar |
| Legal memo         | English and Bengali, printable to PDF                                                                                               |
| Telegram (via n8n) | Daily Radar summary with alerts waiting for a decision                                                                              |
| REST API           | All results as JSON (`docs/API.md`, OpenAPI at `/docs`)                                                                             |
| MCP                | 13 tools for AI agents and IDE hosts                                                                                                |
| Dashboards         | Admin overview, human-review queue, jobs; public `/docs` status page                                                                |

## 8. Data quality

- Extraction: a relation enters the graph only if its quote is found in the source chunk (SVB 2022 proxy: 137 of 162 verified, 85%).
- Retrieval regression: 10 gold questions, hit@1 90%, MRR 0.933.
- Rule-engine regression on SVB: expected and actual results match.
- Reliability Sentinel on every AI finding; unverified findings go to human review.
- Replay leak check: any citation dated after the freeze date makes the run INVALID.
- Two independent SVB Replay runs, both VALID with no missed knowable sign (`docs/REPLAY.md`).

## 9. Privacy and security

- PII redaction of user text (emails, phones, ID and card numbers) before any model call and on chatbot replies; 8 of 8 synthetic items caught, 0 of 6 public sentences altered.
- Private mode: every AI step on local models, fails closed (`docs/LOCAL_MODELS.md`).
- Passwords hashed with argon2id; admin sessions short-lived with a step-up; reviewer emails masked in the Radar audit trail.
- The help chatbot has no database, user or admin access by design and by test.
- Secrets only in git-ignored `.env` files and host secret settings.
- Ollama is never published to the internet; tunnels are temporary.

## 10. Lineage

Every finding carries: filing accession number, form, filing date, section, page, chunk id and the supporting quote.
Every graph relation carries its source quote and page. Every report records the freeze date, retrieval mode,
models used (provider and model name per call) and whether it ran in Private mode.
Prompts are versioned files. The usage log records task, provider, model, tokens, latency and cost per call.

## 11. Cost and performance

- Free tiers only; measured cost per Crash-Test $0.00 (for example 5 LLM calls, 13,079 tokens for an Apple run).
- A cloud Crash-Test takes about 2 to 5 minutes; a Private-mode run on an 8 GB CPU-only laptop took about 7 minutes.
- Costs kept low by caching (filings, embeddings, extraction, analyses), local embeddings and reranking, cheap-model routing for simple steps, and a rule engine with no token cost.

## 12. Open-source stack

FastAPI, Pydantic, LangGraph, psycopg, pgvector, Neo4j driver, DuckDB, fastembed / ONNX Runtime, BeautifulSoup, lxml,
argon2-cffi, PyJWT, pytest, Next.js, React, Tailwind CSS, n8n, Ollama, MCP Python SDK, cloudflared.
