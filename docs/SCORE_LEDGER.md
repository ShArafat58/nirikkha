# SCORE LEDGER: Nirikkha (Pre-Judgment target 425)

Rule: a row is claimed in the form only if its evidence exists in this repo or the live app.
Status: `planned` → `built` (in repo) → `verified` (checked live). `text` = needs only the form text, already backed by repo docs.
Last updated: 22 Oct 2026.

## Summary (estimate)

| Section          | Max     | Built / verified | Text to write                                             | Still planned                                                   |
| ---------------- | ------- | ---------------- | --------------------------------------------------------- | --------------------------------------------------------------- |
| Basics           | 149     | ~118             | 27 (pitch, summary, problem, solution, domain, challenge) | ~4                                                              |
| AI Detail Usage  | 232     | ~206             | —                                                         | ~26 (frontend AI builders 12, fine-tune 4, AI-DLC 8, agentic 4) |
| Links            | 17      | 5                | —                                                         | 12 (YouTube 10, Figma 1, deck 1)                                |
| Build Provenance | 20      | 20               | —                                                         | 0                                                               |
| Team             | 7       | teammate         | —                                                         | 5th member, NRB                                                 |
| **Total**        | **425** | **~349**         | **+27 → ~376**                                            |                                                                 |

## Basics (149)

| #   | Field                                        | Pts | Evidence                                                                                                 | Status                      |
| --- | -------------------------------------------- | --- | -------------------------------------------------------------------------------------------------------- | --------------------------- |
| B1  | Project name                                 | 1   | Nirikkha, `README.md`                                                                                    | built                       |
| B2  | Elevator pitch                               | 2   | `docs/SUBMISSION.md`                                                                                     | text                        |
| B3  | Public summary (tiered)                      | 3   | `docs/SUBMISSION.md`                                                                                     | text                        |
| B4  | Domain                                       | 1   | JusticeSphere AI                                                                                         | text                        |
| B5  | Challenge                                    | 1   | GovernanceIQ                                                                                             | text                        |
| B6  | Problem statement (tiered)                   | 10  | `docs/SUBMISSION.md`                                                                                     | text                        |
| B7  | Solution description (tiered)                | 10  | `docs/SUBMISSION.md`                                                                                     | text                        |
| B8  | Data lifecycle filled                        | 5   | `docs/DATA_LIFECYCLE.md`                                                                                 | built                       |
| B9  | Graph DB                                     | 5   | Neo4j Aura: 115 Organization, 39 Person, 21 Committee nodes; quote + page on each relation; `app/graph/` | verified (MCP query)        |
| B10 | Vector DB                                    | 3   | Supabase pgvector, 1,949 chunks, 384-dim                                                                 | built                       |
| B11 | Lakehouse / warehouse                        | 3   | DuckDB `backend/data/analytics.duckdb`, `app/analytics/`                                                 | built                       |
| B12 | Scrapers / extractors (cap 4)                | 4   | API pull (EDGAR), AI extraction with quote verification, MCP data access, n8n flows                      | built 4/4                   |
| B13 | Parsing: parser, formatter, cleaning, schema | 4   | BeautifulSoup + lxml; contextual headers and Markdown memo; cleaning and name merging; Pydantic          | built 4/4                   |
| B14 | Data source types (cap 5)                    | 5   | External APIs, open/public data (SEC EDGAR), curated (rule changes, Replay case), synthetic (test sets)  | built 4/5 (no user uploads) |
| B15 | Storage targets (cap 4)                      | 4   | Postgres, vector (pgvector), DuckDB, Neo4j                                                               | built 4/4                   |
| B16 | Formats (cap 4)                              | 4   | HTML / inline XBRL, JSON / JSONL, Markdown, PDF (memo export) — choose matching form options             | built                       |
| B17 | Visualization tools (cap 3)                  | 3   | Recharts (`overview.tsx`, `health-panel.tsx`), custom SVG graph and timeline                             | built 1–2/3                 |
| B18 | ML / analytics methods (cap 4)               | 4   | Rule engine, LLM / RAG, statistical analysis (YoY), cross-encoder ranking / graph analytics              | built 4/4                   |
| B19 | Orchestration note ≥50                       | 2   | `docs/DATA_LIFECYCLE.md` §6                                                                              | built                       |
| B20 | Streaming note ≥50                           | 2   | Node events → SSE progress with elapsed timer                                                            | built                       |
| B21 | Privacy note ≥80                             | 3   | `docs/DATA_LIFECYCLE.md` §9, `docs/LOCAL_MODELS.md`                                                      | built                       |
| B22 | Lineage note ≥80                             | 2   | `docs/DATA_LIFECYCLE.md` §10                                                                             | built                       |
| B23 | Data quality note ≥80                        | 2   | `docs/DATA_LIFECYCLE.md` §8, `docs/EVALUATION.md`                                                        | built                       |
| B24 | Publish local to internet                    | 4   | Cloudflare quick tunnel for n8n and MCP, `docs/TUNNEL.md`                                                | verified                    |
| B25 | Publish notes                                | 2   | `docs/TUNNEL.md`                                                                                         | verified                    |
| B26 | ~35 detail fields                            | 60  | `docs/DATA_LIFECYCLE.md` §1–12                                                                           | built                       |

## AI Detail Usage (232)

| #     | Field                                              | Pts | Evidence                                                                                                                                                                                    | Status       |
| ----- | -------------------------------------------------- | --- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------ |
| A1    | LLMs (5)                                           | 15  | gpt-oss-120b, gpt-oss-20b, gpt-oss-safeguard-20b, gemini-2.5-flash, qwen3.8-27b (+ gemini-2.5-flash-lite, qwen2.5:1.5b, gemma3:1b)                                                          | built        |
| A2    | How and why                                        | 5   | `docs/ARCHITECTURE.md` §7                                                                                                                                                                   | built        |
| A3    | ≥1 LLM bonus                                       | 5   | Router with fallback                                                                                                                                                                        | built        |
| A4    | Prompt usage                                       | 10  | 13 versioned prompt files                                                                                                                                                                   | built        |
| A5    | Prompt strategy                                    | 5   | Role prompting, grounding, evidence ids, JSON schema, few-shot in extraction, reasoning effort per task; `docs/PROMPT_LIBRARY.md`                                                           | built        |
| A6–A9 | Token optimization + notes + tools + extra         | 23  | Cheap-model routing, response cache, analysis cache, chunk dedup by hash, per-model RPM/TPM/TPD budgets, structured JSON outputs, local embeddings and reranker, rule engine with no tokens | built        |
| A10   | RAG techniques (4)                                 | 12  | Hybrid (pgvector + full-text, RRF), contextual chunk headers, semantic chunking, cross-encoder rerank                                                                                       | built        |
| A11   | RAG bonus                                          | 5   | `app/rag/retrieve.py`                                                                                                                                                                       | built        |
| A12   | Contextual RAG bonus                               | 5   | `app/ingest/chunk.py`                                                                                                                                                                       | built        |
| A13   | Semantic chunking bonus                            | 3   | `app/ingest/chunk.py`                                                                                                                                                                       | built        |
| A14   | Combo bonus                                        | 3   | Contextual + semantic + hybrid + rerank together                                                                                                                                            | built        |
| A15   | Graph RAG bonus                                    | 5   | Relationship investigation over Neo4j with quoted relations                                                                                                                                 | built        |
| A16   | RAG architecture details                           | 10  | `docs/ARCHITECTURE.md` §1–2                                                                                                                                                                 | built        |
| A17   | MCP servers built (5)                              | 13  | `mcp-servers/`, `docs/MCP.md`, smoke test 5/5                                                                                                                                               | verified     |
| A18   | MCP servers used (5)                               | 8   | Filesystem, Git, Fetch, Neo4j Cypher, Sequential Thinking; `docs/MCP.md` §4                                                                                                                 | verified     |
| A19   | Transports, clients/hosts, reuse                   | 6   | stdio + Streamable HTTP; Antigravity, `smoke_test.py`, `http_check.py`                                                                                                                      | verified     |
| A20   | Frontend AI builders (+notes)                      | 12  | —                                                                                                                                                                                           | planned      |
| A21   | Workflow automation + n8n bonus + notes            | 13  | n8n (2 workflows), LangGraph pipeline; `workflows/`                                                                                                                                         | built ~11    |
| A22   | Local LLM runtimes, Ollama bonus, models, hardware | 25  | Ollama + ONNX Runtime; qwen2.5:1.5b, gemma3:1b, bge-small, ms-marco-MiniLM; `docs/LOCAL_MODELS.md`                                                                                          | verified ~24 |
| A23   | Agentic frameworks                                 | 11  | LangGraph                                                                                                                                                                                   | built ~7     |
| A24   | Agent orchestration notes ≥80                      | 5   | `docs/ARCHITECTURE.md` §3                                                                                                                                                                   | built        |
| A25   | AI-DLC frameworks + process notes                  | 18  | `AGENTS.md`, `docs/SPEC.md`, versioned prompts, tests per step                                                                                                                              | built ~10    |
| A26   | Fine-tuning ≥80                                    | 4   | —                                                                                                                                                                                           | planned      |
| A27   | Evaluation ≥80                                     | 6   | `docs/EVALUATION.md`, Replay                                                                                                                                                                | built        |
| A28   | Guardrails ≥80                                     | 6   | PII redaction, injection filter + safety model, schema validation, citation verification, fail-closed Private mode                                                                          | built        |
| A29   | Open-source tools, other                           | 4   | `docs/DATA_LIFECYCLE.md` §12                                                                                                                                                                | built        |
| —     | `/docs` module                                     | —   | https://nirikkha.vercel.app/docs                                                                                                                                                            | verified     |

## Links (17)

| #   | Link                                          | Pts | Status                   |
| --- | --------------------------------------------- | --- | ------------------------ |
| L1  | YouTube (≤181 s, public or unlisted)          | 10  | planned (teammate)       |
| L2  | GitHub https://github.com/ShArafat58/nirikkha | 2   | verified                 |
| L3  | Live demo https://nirikkha.vercel.app         | 1   | verified                 |
| L4  | Figma / design                                | 1   | planned                  |
| L5  | Other: `/docs` page, API docs, pitch deck     | 3   | 2 verified, deck planned |

## Build Provenance (20)

| #   | Field                      | Pts | Evidence                              | Status   |
| --- | -------------------------- | --- | ------------------------------------- | -------- |
| P1  | Tooling / IDE              | 3   | Google Antigravity (agent + MCP host) | built    |
| P2  | MCP disclosed              | 2   | `docs/MCP.md`                         | built    |
| P3  | Prompt Library (≥1 prompt) | 5   | `docs/PROMPT_LIBRARY.md` (10 prompts) | built    |
| P4  | IDE                        | 1   | Antigravity                           | built    |
| P5  | Frameworks                 | 1   | FastAPI, Next.js, LangGraph           | built    |
| P6  | Deployment                 | 1   | Vercel, Render                        | verified |
| P7  | Context / memory files     | 2   | `AGENTS.md`, `docs/SPEC.md`           | built    |
| P8  | MCP servers list           | 2   | `docs/MCP.md`                         | built    |
| P9  | MCP tools exposed          | 2   | 13 tools, `docs/MCP.md` §1            | built    |
| P10 | MCP permissions            | 1   | `docs/MCP.md` §3                      | built    |

## Team (7)

4 members, at least one female member (done).
