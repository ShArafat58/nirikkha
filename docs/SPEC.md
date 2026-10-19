# SPEC — Nirikkha (Governance Crash-Test AI)

Source of truth for the idea: the GovernanceIQ plan PDF. This spec does not change the idea; it makes it buildable.

## 1. Users and the core job

- Primary user: investment analyst / fund research team doing governance due diligence before a decision.
- Secondary: corporate compliance teams, internal auditors, bank credit/KYC teams.
- Core job: "Before we proceed with <decision>, identify the governance risks and evidence gaps we should investigate."

## 2. Non-negotiable requirements (GovernanceIQ)

1. Read >= 2 filing types: Form 10-K and DEF 14A.
2. Governance Health Score (explainable).
3. Citations + mitigation recommendations for every finding.
4. Verification against a regulatory benchmark (SEC Reg S-K rules) and a real controversy (SVB Replay).

## 3. Priorities

| Priority | Scope                                                                                                                                                       |
| -------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------- |
| P0       | Ingestion (10-K + DEF 14A), 4 investigations, Crash-Test Report, Rule Engine, Reliability Sentinel, Health Score, SVB Replay, polished frontend, live links |
| P1       | Regulatory Change Radar + Approve/Reject, Legal memo, Neo4j relationship graph, n8n workflows, MCP servers                                                  |
| P2       | Local models / private mode, LoRA fine-tune, remaining Pre-Judgment items                                                                                   |

## 4. Pipeline (input -> processing -> output)

1. Input: company (ticker or CIK) + decision text (optional) + optional PDF upload.
2. Ingest: fetch latest and previous-year 10-K and DEF 14A from SEC EDGAR; keep accession number, filing date, section and page.
3. Parse and chunk: clean text, section detection, semantic + contextual chunks, embeddings, vector store.
4. Extract: directors, executives, committees, affiliations, related-person transactions -> relationship graph.
5. Investigate (agents): Relationship, Cross-Document Consistency, Regulatory Rule Check, Missing Evidence — focused on the decision text.
6. Verify: Rule Engine results + Reliability Sentinel checks on every finding.
7. Output: Crash-Test Report, Health Score with explanation, Legal memo, Bengali summary.

## 5. Finding (core data shape)

| Field               | Type           | Notes                                                                                                                          |
| ------------------- | -------------- | ------------------------------------------------------------------------------------------------------------------------------ |
| id                  | string         |                                                                                                                                |
| investigation       | enum           | relationship / consistency / rule_check / missing_evidence                                                                     |
| report_section      | enum           | disclosure_verification / conflict_review / regulatory_check / recommended_action                                              |
| title               | string         |                                                                                                                                |
| claim               | string         | Neutral wording; never alleges misconduct                                                                                      |
| risk_severity       | enum           | low / medium / high / critical                                                                                                 |
| evidence_confidence | enum           | high / medium / low / insufficient                                                                                             |
| citations           | list           | each: doc_type, accession_no, filed_date, section, page, passage                                                               |
| sentinel            | object         | citation_supports_claim, contradiction_found, authoritative_source, period_correct, evidence_sufficient, human_review_required |
| recommended_actions | list of string |                                                                                                                                |

Rule: risk_severity and evidence_confidence are always separate. Low evidence never lowers severity automatically, and never becomes "low risk".

## 6. Governance Rule Engine

- Each rule: id, source (e.g. Reg S-K Item 404), category, requirement, evidence_needed, test, result, evidence, human_review.
- category: `law` / `best_practice` / `internal_indicator` (never mixed).
- result: `PASS` / `POTENTIAL_GAP` / `FAIL` / `INSUFFICIENT_EVIDENCE`.
- First rule set: Regulation S-K Items 401 (directors and executive officers), 402 (executive compensation),
  404 (related-person transactions), 407 (corporate governance: independence, committees, audit committee financial expert).
- Rules are plain data + Python test functions with unit tests. No LLM decides a rule result alone.

## 7. Health Score

- Output: score (0–100), risk factors, evidence strength, missing information, applicable rules.
- Formula: to be designed with the owner before implementation (Day 4).
- Constraint: count of INSUFFICIENT_EVIDENCE items is shown next to the score, never hidden inside it.

## 8. First Warning Sign Replay (signature demo)

1. Timeline: key dates of the controversy from reliable public sources.
2. Reconstruct: collect filings publicly available before the event.
3. Freeze: evidence cutoff date; anything filed after it is excluded from the system.
4. Run: full Crash-Test on frozen evidence only.
5. Compare: findings vs documented outcome — hit / missed / not knowable at the time.

- Case 1: Silicon Valley Bank (SVB Financial Group). Cutoff: before the March 2023 failure. Exact filings and dates to be confirmed from EDGAR.
- Control: 1–2 healthy companies, to show the system does not flag everyone.
- Outcome documents are used only in step 5, never as input.

## 9. Regulatory Change Radar (P1)

- Streams: (a) curated regulatory updates, (b) new EDGAR filings for watched companies.
- For each item: what changed, affected requirements, disclosures to review, evidence status, follow-up action, priority.
- Human-in-the-loop: Approve / Reject before any follow-up action runs. Decision is logged.

## 10. Legal memo (P1)

- Memo format from a Crash-Test: at least 3 non-obvious risks, each citing a real rule; every citation verified by the Sentinel.

## 11. API (draft — full contract in docs/API.md)

| Method | Path                       | Purpose                                  |
| ------ | -------------------------- | ---------------------------------------- |
| GET    | /health                    | Liveness                                 |
| GET    | /companies/search?q=       | Find company by name or ticker           |
| POST   | /filings/ingest            | Fetch 10-K + DEF 14A for a company       |
| POST   | /filings/upload            | Upload a PDF                             |
| POST   | /analyses                  | Start a Crash-Test (company + decision)  |
| GET    | /analyses/{id}/events      | Live progress (Server-Sent Events)       |
| GET    | /analyses/{id}             | Full report                              |
| GET    | /analyses/{id}/memo        | Legal memo                               |
| GET    | /analyses/{id}/graph       | Relationship graph                       |
| GET    | /rules                     | Rule library                             |
| GET    | /replays/{case}            | Replay result (e.g. svb)                 |
| GET    | /radar/items               | Radar items                              |
| POST   | /radar/items/{id}/decision | Approve / Reject                         |
| GET    | /system/status             | Model, cost, cache status for /docs page |

## 12. Cross-cutting

- LLM fallback: Groq -> Gemini -> local. Demo never crashes.
- Cache every analysis; precompute demo companies and the Replay.
- Log tokens, latency and cost per analysis.
- Bengali / English UI toggle; Bengali report summary.
- Public or synthetic data only.
