# AGENTS.md — Rules for AI coding agents working on Nirikkha

Nirikkha (নিরীক্ষা) — "Trust less, Verify more."
Governance Crash-Test AI for the GovernanceIQ challenge (International AI Builders Congress 2026, JusticeSphere AI).
Also covers the Risk Sentinel and Legal Copilot challenges.

## 1. What the product does

Before a company makes a critical decision, Nirikkha tests the governance evidence behind it.
It reads SEC filings (Form 10-K and DEF 14A), runs four investigations
(Relationship, Cross-Document Consistency, Regulatory Rule Check, Missing Evidence),
and produces an evidence-linked Governance Crash-Test Report with an explainable Health Score.
Every finding links to source document + page/section + supporting passage.

Core principles (never violate):

- Evidence-first: no material finding without a verifiable citation.
- Responsible Uncertainty: when evidence is weak, output "Insufficient Evidence" — never guess.
- Evidence Confidence and Risk Severity are always separate fields.
- Never accuse a company of misconduct. A relationship is a "potential conflict requiring review", not proof.
- Applicable law, best practice and internal risk indicators are kept separate.

## 2. Repository layout

| Folder         | Purpose                                                         | Who edits         |
| -------------- | --------------------------------------------------------------- | ----------------- |
| `frontend/`    | Next.js UI                                                      | Teammates + owner |
| `backend/`     | FastAPI API, agents, rule engine                                | Owner only        |
| `mcp-servers/` | Our own MCP servers (FastMCP)                                   | Owner             |
| `workflows/`   | n8n workflow exports (JSON)                                     | Owner             |
| `notebooks/`   | Fine-tuning and evaluation notebooks                            | Owner             |
| `data/`        | Demo data, curated regulatory updates, Replay snapshots         | Owner             |
| `docs/`        | Architecture, API contract (`docs/API.md`), specs, score ledger | Owner             |

## 3. Hard rules

1. Frontend and backend share NO code. Frontend talks to backend only via the REST API in `docs/API.md`.
2. Frontend reads the backend URL only from `NEXT_PUBLIC_API_URL`. Frontend must support a mock mode.
3. If an API response shape changes, update `docs/API.md` in the same commit.
4. No API keys or secrets in code, ever. Use `.env` (git-ignored) and keep `.env.example` up to date.
5. 100% free stack. Do not add paid services or SDKs that require a paid plan.
6. LLM calls must go through one client with fallback: Groq -> Gemini -> local (Ollama). The demo must never crash.
7. Every external call has error handling and a clear user-facing message (rate limit, API down, unreadable PDF).
8. SEC EDGAR: always send a `User-Agent` header with name + email, and stay under the requests-per-second limit.
9. Cache analyses in the database. Demo companies and the Replay are precomputed.
10. Log tokens, latency and cost for every analysis.
11. Use only public or synthetic data. Never real personal data in the demo.
12. Never claim a feature in docs or the submission form that is not built and visible in this repo.

## 4. Code style

- Python 3.12, FastAPI, type hints, `pytest` tests in `backend/tests/`.
- TypeScript + Next.js (App Router) in `frontend/`.
- Code and comments in English.
- Always give complete files, never partial snippets.
- Commit after each working step. Message format: `type: short description`
  (types: feat, fix, chore, docs, test, refactor).

## 5. Where to look

- Product idea and business model: `docs/` (plan PDF summary) and the project brief.
- Current status: `PROGRESS.md`.
- Pre-Judgment score tracking: `docs/SCORE_LEDGER.md`.
- API contract: `docs/API.md`.
