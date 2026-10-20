# SCORE LEDGER - Nirikkha (Pre-Judgment target: 425)

Rule: a row is only claimed in the form when status = **verified** and the evidence path exists in this repo or the live app.
Status: `planned` -> `built` (in repo) -> `verified` (checked live / in form).

## Summary
| Section | Max | Built | Verified |
|---|---|---|---|
| Basics | 149 | 26 | 0 |
| AI Detail Usage | 232 (brief table sums 237 - confirm with live form) | 42 | 0 |
| Links | 17 | 3 | 0 |
| Build Provenance | 20 | 3 | 0 |
| Team | 7 | - | - |
| **Total** | **425** | **74** | **0** |

## Basics (149)
| # | Field | Pts | What we build / write | Evidence path | Status |
|---|---|---|---|---|---|
| B1 | Project name | 1 | Nirikkha | `README.md` | built |
| B2 | Elevator pitch (>=20 chars) | 2 | From plan PDF | `docs/SUBMISSION.md` | planned |
| B3 | Public summary (tiered) | 3 | Long structured summary | `docs/SUBMISSION.md` | planned |
| B4 | Domain | 1 | JusticeSphere AI | `docs/SUBMISSION.md` | planned |
| B5 | Challenge | 1 | GovernanceIQ | `docs/SUBMISSION.md` | planned |
| B6 | Problem statement (tiered) | 10 | Long, specific | `docs/SUBMISSION.md` | planned |
| B7 | Solution description (tiered) | 10 | Long, specific | `docs/SUBMISSION.md` | planned |
| B8 | Data lifecycle filled | 5 | Every section filled | `docs/DATA_LIFECYCLE.md` | planned |
| B9 | Graph DB | 5 | Neo4j Aura: Person / Company / Committee / Organization / Party / Filing; SVB 2022 proxy loaded (134 relationships, each with quote + page) | `backend/app/graph/store.py` | built |
| B10 | Vector DB | 3 | Supabase Postgres 17 + pgvector 0.8.2, HNSW index, 1,688 chunks (384-dim) | `backend/sql/`, `backend/app/rag/store.py` | built |
| B11 | Lakehouse / Warehouse | 3 | DuckDB warehouse: YoY section change + term trends | `backend/app/analytics/warehouse.py` | built |
| B12 | Advanced scrapers / extractors (cap 4) | 4 | Built: SEC EDGAR API pull, AI extraction with quote verification (2). Candidates: OCR, MCP data access | `backend/app/ingest/edgar.py`, `backend/app/graph/extract.py` | built (2/4) |
| B13 | Advanced parsing (parsers, formatters, cleaning, schema) | 4 | Built: BeautifulSoup+lxml parser, HTML cleaning, Pydantic schema validation (3). Formatter pending | `backend/app/ingest/parse.py` | built (3/4) |
| B14 | Data source types (cap 5) | 5 | Built: External API (SEC EDGAR) (1). Planned: user uploads, curated regulatory updates, open datasets | `docs/DATA_LIFECYCLE.md` | built (1/5) |
| B15 | Storage targets (cap 4) | 4 | Built: Postgres, Vector (pgvector), DuckDB, Neo4j (4) | `docs/DATA_LIFECYCLE.md` | built (4/4) |
| B16 | Formats (cap 4) | 4 | Built: HTML/XHTML (inline XBRL), JSON/JSONL (2). Planned: PDF uploads | `docs/DATA_LIFECYCLE.md` | built (2/4) |
| B17 | Visualization tools (cap 3) | 3 | Chosen at frontend step | `frontend/` | planned |
| B18 | ML / analytics methods (cap 4) | 4 | Built: Statistical analysis (YoY, term trends), LLM/RAG (2). Planned: Rule Engine, graph analytics | `backend/app/analytics/`, `backend/app/rag/` | built (2/4) |
| B19 | Orchestration note (>=50) | 2 | Real description | `docs/DATA_LIFECYCLE.md` | planned |
| B20 | Streaming note (>=50) | 2 | Real description (e.g. SSE progress) | `docs/DATA_LIFECYCLE.md` | planned |
| B21 | Privacy note (>=80) | 3 | Local embeddings + reranker, Data API off + RLS, Gemini free-tier data note | `docs/DATA_LIFECYCLE.md` | planned |
| B22 | Lineage note (>=80) | 2 | Accession no -> section/page -> paragraph -> chunk -> extracted relation (quote) -> graph edge -> finding | `docs/DATA_LIFECYCLE.md` | planned |
| B23 | Data quality note (>=80) | 2 | Schema validation, TOC folding, quote verification (85% verified), table-evidence flag, rerank thresholds | `docs/DATA_LIFECYCLE.md` | planned |
| B24 | Publish local to internet | 4 | Tunnel for local services | `docs/DEPLOY.md` | planned |
| B25 | Publish notes | 2 | Real description | `docs/DEPLOY.md` | planned |
| B26 | ~35 detail fields (1-3 each) | 60 | Every field truthful; exact split to confirm on live form | `docs/DATA_LIFECYCLE.md` | planned |

## AI Detail Usage (232)
| # | Field | Pts | What we build | Evidence path | Status |
|---|---|---|---|---|---|
| A1 | LLMs (each +3, max 15) | 15 | In pipeline so far: qwen/qwen3.8-27b (extraction), openai/gpt-oss-20b (extraction fallback, fast tasks), gemini-2.5-flash (fallback) = 9. Planned roles: gpt-oss-120b (investigations, memo), gemini-2.5-flash (Bengali summary), gpt-oss-safeguard-20b (input guardrail) | `backend/app/llm/client.py` | built (9/15) |
| A2 | LLM "how & why" | 5 | Real description | `docs/AI_DETAILS.md` | planned |
| A3 | >=1 LLM bonus | 5 | LLM router with fallback in use | `backend/app/llm/client.py` | built |
| A4 | Prompt usage | 10 | Versioned prompt files (extract_governance v1, v2); more to come | `backend/app/prompts/` | planned |
| A5 | Prompt strategy | 5 | Role prompting, rules, few-shot (prose + table), JSON output, quote-or-nothing | `docs/AI_DETAILS.md` | planned |
| A6 | Token optimization | 10 | So far: model routing, response cache, per-model RPM/TPM/TPD budgets, section-filtered extraction, chunk dedup, local embeddings + reranker, non-AI DuckDB analytics | `backend/app/llm/`, `backend/app/graph/extract.py` | planned |
| A7 | Token optimization notes | 3 | Real description | `docs/AI_DETAILS.md` | planned |
| A8 | Token optimization tools (cap 4) | 4 | Tools really used | `backend/` | planned |
| A9 | Token optimization extra | 6 | Per brief | `backend/` | planned |
| A10 | RAG techniques (each +3, max 12) | 12 | Hybrid search (pgvector + full-text, RRF), contextual chunk headers, semantic chunking, cross-encoder reranker | `backend/app/rag/`, `backend/app/ingest/chunk.py` | built (12/12) |
| A11 | RAG bonus | 5 | RAG pipeline in use (`retrieve()`) | `backend/app/rag/retrieve.py` | built |
| A12 | Contextual RAG bonus | 5 | Contextual header prepended to every embedded chunk | `backend/app/ingest/chunk.py` | built |
| A13 | Semantic chunking bonus | 3 | Topic-shift breakpoints from paragraph embeddings | `backend/app/ingest/chunk.py` | built |
| A14 | RAG combo bonus | 3 | Contextual + semantic + hybrid + rerank together | `backend/app/rag/` | built |
| A15 | Graph RAG bonus | 5 | Neo4j-backed retrieval (graph built; retrieval in agents next) | `backend/app/graph/` | planned |
| A16 | RAG architecture details | 10 | Real description (5+5) | `docs/AI_DETAILS.md` | planned |
| A17 | MCP servers built (cap 5) | 13 | 5 FastMCP servers (10+3) | `mcp-servers/` | planned |
| A18 | MCP servers used (cap 5) | 8 | 5 existing servers really used (5+3). Candidates: Render MCP, Supabase MCP | `docs/MCP.md` | planned |
| A19 | MCP transports / clients / reuse notes | 6 | stdio + Streamable HTTP etc. (2+2+2) | `docs/MCP.md` | planned |
| A20 | Frontend AI builders (max 5) + notes | 12 | Only builders really used (5+5+2) | `docs/AI_DETAILS.md` | planned |
| A21 | Workflow automation + n8n bonus + notes | 13 | n8n + LangGraph + others (4+2+5+2) | `workflows/` | planned |
| A22 | Local LLM runtimes + Ollama bonus | 10 | Ollama + others really used (3+2+5). fastembed (ONNX Runtime) already runs bge-small + MiniLM locally | `backend/app/llm/` | planned |
| A23 | Local models (2 each, max 8) + notes | 13 | Small CPU models (8+5). Candidates: bge-small-en-v1.5, ms-marco-MiniLM-L-6-v2 | `docs/AI_DETAILS.md` | planned |
| A24 | Hardware notes | 2 | 16 GB RAM, Intel UHD, CPU inference | `docs/AI_DETAILS.md` | planned |
| A25 | Agentic frameworks (cap 5) | 11 | LangGraph main + others (5+6) | `backend/app/agents/` | planned |
| A26 | Agent orchestration notes (>=80) | 5 | Real description (2+3) | `docs/AI_DETAILS.md` | planned |
| A27 | AI-DLC frameworks + process notes | 18 | AGENTS.md (root + frontend), SPEC.md, PROGRESS.md really followed (3+8+3+4) | `AGENTS.md`, `docs/SPEC.md` | built (partial) |
| A28 | Fine-tuning (>=80) | 4 | Small LoRA on Colab/Kaggle (2+2) | `notebooks/` | planned |
| A29 | Evaluation (>=80) | 6 | Regression set + Replay (3+3). So far: 67 pytest tests, quote verification rate | `backend/tests/`, `notebooks/` | planned |
| A30 | Guardrails (>=80) | 6 | PII, input check, schema, citation check (3+3). Quote verification already blocks unsupported relations | `backend/app/guardrails/` | planned |
| A31 | Open-source tools + other notes | 4 | Real list (3+1) | `docs/AI_DETAILS.md` | planned |

Note: A1-A31 as listed in the brief sum to 237; the form says 232. Fix rows after checking the live form.

## Links (17)
| # | Field | Pts | Evidence | Status |
|---|---|---|---|---|
| L1 | YouTube (<=181 s, Public/Unlisted) | 10 | Teammate video | planned |
| L2 | GitHub | 2 | https://github.com/ShArafat58/nirikkha | built |
| L3 | Live demo | 1 | https://nirikkha.vercel.app | built |
| L4 | Figma / design | 1 | Logo + design file | planned |
| L5 | Other links | 3 | /docs page, pitch deck, HF model card | planned |

## Build Provenance (20)
| # | Field | Pts | Evidence | Status |
|---|---|---|---|---|
| P1 | Tooling / IDE | 3 | Google Antigravity + AI assistants used | planned |
| P2 | MCP disclosed | 2 | `docs/MCP.md` | planned |
| P3 | >=1 prompt in Prompt Library | 5 | 10+ real prompts (extract_governance v1/v2 exist) | planned |
| P4 | IDE | 1 | Google Antigravity | planned |
| P5 | Frameworks | 1 | FastAPI, Next.js, LangGraph | planned |
| P6 | Deployment | 1 | Vercel (frontend) + Render (backend) | built |
| P7 | Context / memory files | 2 | `AGENTS.md`, `frontend/AGENTS.md`, `PROGRESS.md` | built |
| P8 | MCP servers list | 2 | `docs/MCP.md` | planned |
| P9 | MCP tools exposed | 2 | `docs/MCP.md` | planned |
| P10 | MCP permissions | 1 | `docs/MCP.md` | planned |

## Team (7) - exact per-item split to confirm on live form
| # | Field | Status |
|---|---|---|
| T1 | 5 members | 4 of 5 - teammate handling |
| T2 | >=1 NRB member | teammate handling |
| T3 | >=1 female member | done |

Built total = Basics (B1 1 + B9 5 + B10 3 + B11 3 + B12 2 + B13 3 + B14 1 + B15 4 + B16 2 + B18 2 = 26)
+ AI (A1 9 + A3 5 + A10 12 + A11 5 + A12 5 + A13 3 + A14 3 = 42) + Links (3) + Provenance (3) = 74.