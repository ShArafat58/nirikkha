# Nirikkha API

The frontend talks to the backend **only** through this REST API. Interactive docs: `<API_URL>/docs`.

| Environment | `NEXT_PUBLIC_API_URL` |
|---|---|
| Local backend | `http://localhost:8000` |
| Deployed backend | `https://nirikkha-api.onrender.com` (free tier: the first request after idle can take ~1 minute) |
| No backend | set `NEXT_PUBLIC_USE_MOCK=true` (sample JSON in the frontend) |

All responses are JSON. Errors use `{"detail": "<human-readable message>"}`; show `detail` to the user as it is.

## Endpoints

| Method | Path | Purpose |
|---|---|---|
| GET | `/health` | Liveness, configured providers (never secrets), `memory_mb` on Linux |
| GET | `/api/companies` | Companies with loaded filings and their latest finished Crash-Tests |
| POST | `/api/crash-tests` | Start a Crash-Test, or get the cached one |
| GET | `/api/crash-tests/{id}` | Poll status, live node events, full report when done |
| POST | `/api/crash-tests/{id}/memo` | Create (or return the cached) legal memo |
| GET | `/api/crash-tests/{id}/memo` | The cached legal memo (404 if none yet) |
| GET | `/api/evaluation` | Latest evaluation results |
| GET | `/api/status` | Live mode (`inline` or `worker`), whether an analysis worker is online, reranker on/off |

## Start a Crash-Test

`POST /api/crash-tests`

```json
{
  "cik": "719739",
  "as_of": "2023-03-10",
  "decision": "Before we proceed with a deposit partnership with this bank, identify the governance risks and evidence gaps we should investigate."
}
```

- `cik`: SEC Central Index Key, 1 to 10 digits (SVB `719739`, Apple `320193`).
- `as_of`: evidence freeze date (optional, default today). Filings after it are invisible to every step.
- `decision`: optional, max 1,500 characters. Personal data (email, phone, ID and card numbers) is redacted before it is stored or sent to any model.

Responses:

| Code | Body | Meaning |
|---|---|---|
| 200 | `{"id": "...", "status": "done", "cached": true}` | Same company, date and decision already analysed: open it immediately |
| 202 | `{"id": "...", "status": "queued", "cached": false}` | Started: poll `GET /api/crash-tests/{id}` |
| 422 | `detail` | Invalid cik, future `as_of`, or decision too long |
| 429 | `detail` | Another live run is in progress (one at a time on the free tier): suggest a precomputed demo |
| 503 | `detail` | Database unreachable |

## Poll a Crash-Test

`GET /api/crash-tests/{id}`: poll every 2-3 seconds while `status` is `queued` or `running`.

```json
{
  "id": "e3d02af1-...", "cik": "0000719739", "as_of": "2023-03-10", "decision": "...",
  "status": "running",
  "pipeline": ["redact", "guard", "collect", "plan", "gather", "analyze", "relationship", "consistency",
               "regulatory", "missing_evidence", "merge", "sentinel", "score"],
  "done_nodes": ["redact", "guard", "collect"],
  "events": [{"node": "collect", "message": "4 filings, 134 graph facts, 14 rules evaluated", "ms": 43676}],
  "report": null, "memo": null, "error": null, "source": "live",
  "created_at": "...", "updated_at": "..."
}
```

`status`: `queued` -> `running` -> `done` | `failed` (see `error`) | `blocked` (input guard; see `error`).
A run with no progress for 15 minutes becomes `failed` ("Timed out").

```js
async function waitForCrashTest(id) {
  while (true) {
    const job = await fetch(`${API}/api/crash-tests/${id}`).then(r => r.json());
    renderProgress(job.pipeline, job.done_nodes, job.events);
    if (!["queued", "running"].includes(job.status)) return job;
    await new Promise(r => setTimeout(r, 2500));
  }
}
```

### The report (`status = done`)

| Key | Content |
|---|---|
| `company`, `cik`, `as_of`, `decision` | What was analysed (decision already redacted) |
| `health` | `score` (0-100), `band`, `coverage` {`pct`, `label`}, `insufficient_evidence` {`count`, `items`}, `factors` (points per finding), `by_investigation`, `excluded`, `human_review`, `warnings`, `formula` |
| `sections` | The four report sections: `disclosure_verification`, `conflict_review` (+ `note`), `regulatory_check` (+ `rules`, `note`), `recommended_actions` (`human_review_first`, `actions`) |
| `findings` | Every finding: `id`, `title`, `claim`, `investigation`, `risk_severity`, `evidence_confidence`, `citations` (form, accession, page, quote), `recommended_actions`, `source` (`deterministic` or `llm`), `sentinel` (`verdict`, `human_review`, `original_confidence`, `checks`) |
| `rule_report` | Governance Rule Engine results: `rule_id`, `source` (rule), `category` (`law`, `best_practice`, `internal_indicator`), `result` (`PASS`, `POTENTIAL_GAP`, `FAIL`, `INSUFFICIENT_EVIDENCE`, `NOT_APPLICABLE`), `rationale`, `evidence` |
| `questions`, `analysis` | Decision-specific questions and the analyst's answers |
| `summary` | Counts by severity, confidence, investigation, source; `sentinel` verdict counts |
| `usage` | LLM calls, input/output tokens, cost (USD), per call: node, provider, model, latency |
| `pii_redacted`, `guard` | Counts of redacted personal data; input guard result |

Each section item carries `citations[].source_url`, a link to the filing on SEC EDGAR.
Show **severity and confidence separately**; never merge them into one colour.

## Legal memo

`POST /api/crash-tests/{id}/memo` (only when the Crash-Test is `done`, otherwise 409). Takes ~6 s the first time,
then it is cached.

```json
{
  "cached": false,
  "memo": {
    "status": "complete", "status_note": "", "executive_summary": "...",
    "risks": [{"title": "...", "severity": "high", "finding_ids": ["CON-3", "REL-8"], "rules": ["Reg S-K Item 407(h)"],
               "analysis": "...", "why_non_obvious": "...", "recommended_action": "...",
               "needs_human_review": true, "absence_claim": false, "rule_wording": true,
               "evidence": [{"finding_id": "CON-3", "form": "10-K", "page": 22, "quote": "...", "source_url": "..."}]}],
    "evidence_gaps": [{"id": "MIS-3", "title": "..."}], "dropped": [], "disclaimer": "..."
  },
  "markdown": "# Legal Risk Memo: ..."
}
```

`status`: `complete` (3-5 verified risks), `insufficient` (fewer passed the citation checks; say so), `unavailable`
(model down; not cached, try again). Show `needs_human_review`, `absence_claim` and `rule_wording` as visible flags.

## Companies

`GET /api/companies` returns
`[{"cik", "company", "filing_count", "chunk_count", "filings": [{accession_no, form, filing_date, has_page_markers, url}], "crash_tests": [{id, as_of, decision, score, band, coverage_pct, has_memo, source, updated_at}]}]`.
Use `crash_tests` to offer precomputed demos that open instantly.

## Evaluation

`GET /api/evaluation` returns the latest `python -m evaluation.run` results: `retrieval` (`hit_at_1`, `hit_at_3`, `mrr`, `rows`),
`injection`, `pii`, `reports` (`rules`, `sentinel`, `health`, `memo`), `run_at`.

## Live modes

| `RUN_JOBS_INLINE` | Who runs a new Crash-Test |
|---|---|
| `true` (local default) | The API process itself |
| `false` (Render free, 512 MB) | The API only queues it. `python -m app.api.worker` on a machine with enough memory claims it, runs the full pipeline and writes progress to the same database. |

In worker mode `POST /api/crash-tests` and `GET /api/crash-tests/{id}` (while `queued`) include `worker_online`.
If no worker picks a job up within 5 minutes it becomes `failed` with a clear message. Before offering a new live
analysis, call `GET /api/status`; when `worker_online` is false, offer the precomputed demos instead.
Each finished report states its `retrieval_mode`.

## Changing the API

The backend owner updates this file whenever a response shape changes and lists the affected frontend pages.