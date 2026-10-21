<p align="center"><img src="frontend/public/brand/logo.svg" alt="Nirikkha logo" width="320"></p>

# Nirikkha (নিরীক্ষা)

**Trust less, Verify more.**

Governance Crash-Test AI: before a company makes a critical decision, test the governance evidence behind it.

Built for the **GovernanceIQ** challenge · International AI Builders Congress 2026 · JusticeSphere AI.
Also covers the **Risk Sentinel** and **Legal Copilot** challenges.

|                         |                                        |
| ----------------------- | -------------------------------------- |
| Live app                | https://nirikkha.vercel.app            |
| Live API (OpenAPI docs) | https://nirikkha-api.onrender.com/docs |
| Project docs page       | https://nirikkha.vercel.app/docs       |

> The free backend sleeps when idle. The first request after a pause can take about a minute.

## What it does

A user picks a SEC-listed company, types the decision they are about to make
("Before we proceed with this partnership…"), and Nirikkha:

1. Reads the company's **Form 10-K** and **DEF 14A / PRE 14A** proxy statements from SEC EDGAR, keeping page and section numbers.
2. Runs **four investigations** focused on that decision: Relationship, Cross-Document Consistency (including year over year), Regulatory Rule Check, and Missing Evidence.
3. Checks structured, testable rules from **Regulation S-K Items 401, 402, 404 and 407** with four results: Pass, Potential Gap, Fail, Insufficient Evidence. Applicable law, best practice and internal risk indicators are kept separate.
4. Lets the **AI Reliability Sentinel** check every AI finding: does the citation support the claim, is there contradictory evidence, is the reporting period right, is human review needed.
5. Produces a **Governance Crash-Test Report** with an explainable **Health Score**. Evidence Confidence and Risk Severity are separate, and "Insufficient Evidence" is shown, never counted as low risk. Every finding links to the filing, page and supporting passage.
6. Turns the report into a **Legal memo** (English and Bengali) with verified citations.

Also in the product:

- **First Warning Sign Replay:** Silicon Valley Bank, using only filings public before 7 March 2023, compared with the documented outcome, plus a healthy-company control (Apple). See `docs/REPLAY.md`.
- **Regulatory Change Radar:** two data streams (curated SEC rule changes + new EDGAR filings), prioritised alerts, and human **Approve / Reject** with an audit trail. Scheduled by n8n with Telegram alerts.
- **Relationship graph:** directors, executives, committees and outside organisations in Neo4j, with board interlocks.
- **Private mode:** every AI step on local Ollama models; fails closed, never falls back to the cloud. See `docs/LOCAL_MODELS.md`.
- **Nirikkha Guide:** a help chatbot (EN/BN) answering only from a curated public help guide.
- **Bengali / English** interface and Bengali report summaries.
- **Pricing** page with the plans from the business plan (no live payment).

## Repository layout

| Folder         | What lives here                                                                                 | Who edits      |
| -------------- | ----------------------------------------------------------------------------------------------- | -------------- |
| `frontend/`    | Next.js app (UI). Talks to the backend only through the REST API                                | Teammates      |
| `backend/`     | FastAPI app: ingestion, retrieval, LangGraph agents, rule engine, Sentinel, Replay, Radar       | Core developer |
| `mcp-servers/` | Five MCP servers of our own (filings, rules, graph, crash-test, regulation)                     | Core developer |
| `workflows/`   | n8n workflow exports (daily Radar scan, backend warm-up)                                        | Core developer |
| `notebooks/`   | Fine-tuning and evaluation notebooks                                                            | Core developer |
| `docs/`        | Architecture, API contract, data lifecycle, prompts, ethics, Replay, local models, score ledger | Everyone       |

## Quick start

### Option A: frontend only (no Python, no keys) — for design work

Windows (PowerShell):

```powershell
git clone https://github.com/ShArafat58/nirikkha.git
cd nirikkha\frontend
Copy-Item .env.example .env.local
npm install
npm run dev
```

macOS (Terminal):

```bash
git clone https://github.com/ShArafat58/nirikkha.git
cd nirikkha/frontend
cp .env.example .env.local
npm install
npm run dev
```

Open http://localhost:3000. In `.env.local`:

- `NEXT_PUBLIC_USE_MOCK=true` uses built-in sample data, no backend needed.
- or `NEXT_PUBLIC_API_URL=https://nirikkha-api.onrender.com` with `NEXT_PUBLIC_USE_MOCK=false` uses the live backend.

### Option B: full stack on your machine

Needs Python 3.12, Node.js (tested with 24), and free accounts for Groq, Google AI Studio, Supabase (Postgres + pgvector) and Neo4j Aura.

Windows:

```powershell
cd nirikkha\backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env        # fill in your own keys; never commit .env
uvicorn app.main:app --port 8000   # terminal 1
python -m app.api.worker           # terminal 2: runs queued Crash-Tests
```

macOS:

```bash
cd nirikkha/backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --port 8000
python -m app.api.worker
```

Database tables: run the files in `backend/sql/` in number order (Supabase SQL editor or `psql`).
Then start the frontend as in Option A with `NEXT_PUBLIC_API_URL=http://localhost:8000`.

More detail: `backend/README.md`, `frontend/README.md`.

### Optional parts

| Part                        | How                                                                 | Doc                    |
| --------------------------- | ------------------------------------------------------------------- | ---------------------- |
| Private mode (local models) | Install Ollama, `ollama pull qwen2.5:1.5b`, `ollama pull gemma3:1b` | `docs/LOCAL_MODELS.md` |
| MCP servers                 | `cd mcp-servers`, create venv, `python smoke_test.py`               | `docs/MCP.md`          |
| n8n workflows               | Docker, import the JSON files                                       | `workflows/README.md`  |
| Public tunnel               | `cloudflared tunnel --url http://localhost:5678`                    | `docs/TUNNEL.md`       |

## Tests

```powershell
cd backend
.\.venv\Scripts\python.exe -m pytest -q     # 234 tests
cd ..\frontend
npm run build
```

## Documentation

| File                     | Topic                                                |
| ------------------------ | ---------------------------------------------------- |
| `docs/SPEC.md`           | Product specification                                |
| `docs/API.md`            | REST API contract for the frontend                   |
| `docs/ARCHITECTURE.md`   | System design, models and why                        |
| `docs/DATA_LIFECYCLE.md` | Sources, parsing, storage, lineage, quality, privacy |
| `docs/PROMPT_LIBRARY.md` | Versioned prompts and how they are used              |
| `docs/ETHICS.md`         | Responsible AI, safeguards, bias and limitations     |
| `docs/REPLAY.md`         | First Warning Sign Replay method and results         |
| `docs/LOCAL_MODELS.md`   | Private mode, local models, measured speed           |
| `docs/MCP.md`            | MCP servers built and used                           |
| `docs/TUNNEL.md`         | Publishing local services                            |
| `docs/HELP_KB.md`        | Public help guide used by the chatbot                |
| `AGENTS.md`              | Rules for AI coding agents working on this repo      |

## Responsible use

Nirikkha does not accuse any company of misconduct. A relationship or gap is a question to investigate,
not proof. When public evidence is not enough, the report says "Insufficient Evidence".
It is decision support for analysts, not legal or investment advice. The Apple partnership story in the
pitch is hypothetical; the live demo uses real public SEC filings.

## Secrets

All keys live in `.env` files that are git-ignored. `.env.example` files list the names only.
