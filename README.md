<p align="center"><img src="frontend/public/brand/logo.svg" alt="Nirikkha logo" width="320"></p>

# Nirikkha (নিরীক্ষা)

**Trust less, Verify more.**

Governance Crash-Test AI - test the governance evidence behind a decision before you make it.

Built for the **GovernanceIQ** challenge · International AI Builders Congress 2026 · JusticeSphere AI.

- Live app: https://nirikkha.vercel.app
- Live API: https://nirikkha-api.onrender.com/docs

## Repository layout

| Folder | What lives here |
|---|---|
| `frontend/` | Next.js app (UI). See `frontend/README.md`. |
| `backend/` | FastAPI app (API, agents, rule engine). See `backend/README.md`. |
| `mcp-servers/` | Our own MCP servers. |
| `workflows/` | n8n workflow exports (JSON). |
| `notebooks/` | Fine-tuning and evaluation notebooks (Colab). |
| `data/` | Demo data, curated regulatory updates, Replay evidence snapshots. |
| `docs/` | Spec, design, API contract, score ledger. |

## Run it

- Frontend only (no Python, no keys): see `frontend/README.md` - mock mode or live backend.
- Backend: see `backend/README.md`.