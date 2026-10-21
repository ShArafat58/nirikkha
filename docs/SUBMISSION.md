# Submission text (copy into the form)

## Project name

Nirikkha (নিরীক্ষা) — Governance Crash-Test AI

## Domain / Challenge

JusticeSphere AI · GovernanceIQ (also covers Risk Sentinel and Legal Copilot)

## Elevator pitch

Before a company makes a critical decision, Nirikkha crash-tests the governance evidence behind it: it reads SEC filings, runs four investigations, checks Regulation S-K rules, verifies every AI finding, and shows what is proven, what is a potential gap and what public evidence cannot confirm. Trust less, verify more.

## Public summary

Nirikkha is a governance decision-intelligence tool for investment analysts, compliance teams, banks and auditors. A user names a SEC-listed company and the decision they are about to make, for example "Before we proceed with this partnership, identify the governance risks and evidence gaps we should investigate." Nirikkha reads the company's Form 10-K and proxy statements (DEF 14A and PRE 14A) from SEC EDGAR, keeps every page and section, and runs four investigations focused on that decision: relationships and potential conflicts of interest, cross-document and year-over-year consistency, a regulatory rule check, and missing evidence.

The result is a Governance Crash-Test Report. Every finding links to the filing, page and exact passage. A Governance Rule Engine tests Regulation S-K Items 401, 402, 404 and 407 with four results: Pass, Potential Gap, Fail and Insufficient Evidence, keeping law, best practice and internal risk indicators separate. An AI Reliability Sentinel checks whether each citation really supports its claim and sends doubtful findings to human review. The explainable Health Score keeps Risk Severity and Evidence Confidence apart, and lists "Insufficient Evidence" instead of hiding it in the number. A legal memo in English and Bengali turns the report into at least three non-obvious risks with verified citations.

To prove usefulness, the First Warning Sign Replay re-runs Nirikkha on Silicon Valley Bank using only filings public before 7 March 2023. All five knowable warning signs were raised as findings or open questions, none was missed, and a second independent run and a healthy-company control (Apple) confirm the result. A Regulatory Change Radar watches two data streams (SEC rule changes and new EDGAR filings) and asks a person to approve or reject each follow-up. A Private mode runs every AI step on local models for confidential documents. The whole system runs on free tiers at a measured cost of $0.00 per analysis.

## Problem statement

Governance failures are usually visible in hindsight. After a collapse, investigators find the signals in documents that were public all along: a key risk role left empty, a board committee structure that looked fine on paper, incentives tied to growth rather than risk, disclosures that quietly changed from one year to the next. Silicon Valley Bank is a recent example: its Chief Risk Officer seat was without a permanent holder for most of 2022, and after its failure the Federal Reserve's review found that the board and management did not manage the bank's risks effectively.

The evidence exists, but it is fragmented. One governance question can need the proxy statement for directors and compensation, the annual report for risk factors, last year's filing for comparison, and the regulation itself to know what must be disclosed. An analyst preparing an investment, a partnership, a credit line or a supplier decision spends hours opening documents and still cannot be sure nothing was missed.

General AI tools make this worse in a different way. They produce fluent summaries without showing where each statement comes from, they rarely say "the public evidence is not enough", and they treat a serious but weakly evidenced concern the same as a proven fact. For a compliance or legal team, an answer that cannot be traced to a page is not usable, and an answer that silently guesses is dangerous. Teams need a tool that investigates around the specific decision they face, separates what is proven from what is only a question, and makes every conclusion verifiable before money or reputation is committed.

## Solution description

Nirikkha turns fragmented corporate disclosures into verifiable, decision-specific governance evidence.

1. **Decision-specific stress test.** The user types the decision. A planner turns it into precise questions that public filings could answer, spread over four investigations.
2. **Evidence-first retrieval.** Filings are chunked by section and meaning, each chunk carries a contextual header (company, form, date, section, pages), and retrieval combines vector search, full-text search and a cross-encoder reranker. An evidence freeze date hides anything published later.
3. **Four investigations.** Relationship Investigation uses a Neo4j graph of directors, executives, committees and outside organisations, built only from relations whose quote was verified in the filing. Cross-Document Consistency compares filings and years. Regulatory Rule Check runs 16 testable rules. Missing Evidence Detection lists what the filings cannot answer.
4. **Governance Rule Engine.** Deterministic, testable rules from Regulation S-K Items 401, 402, 404 and 407 with Pass, Potential Gap, Fail, Insufficient Evidence or Not applicable (for example, bank-specific best practices do not apply to a technology company).
5. **AI Reliability Sentinel.** A second, stronger model checks every AI finding against its cited evidence, the reporting period and contradictions; anything not verified goes to a human-review queue.
6. **Explainable Health Score.** Each deduction is listed with its finding; severity and confidence are separate; insufficient evidence is shown, not counted as low risk.
7. **Legal memo (Legal Copilot).** At least three non-obvious risks that combine findings and cite real rules; every citation is re-checked; Bengali translation available.
8. **First Warning Sign Replay.** A five-step historical test on SVB with a hindsight guard and a leak check, plus a control company.
9. **Regulatory Change Radar (Risk Sentinel).** Two data streams, prioritised alerts, human Approve/Reject with an audit trail, daily n8n schedule with Telegram alerts.
10. **Private mode.** Every AI step on local Ollama models; it stops rather than falling back to the cloud.

Built with FastAPI, LangGraph, Supabase Postgres + pgvector, Neo4j, DuckDB, Next.js, five custom MCP servers, n8n and Ollama; 234 automated tests; deployed on Vercel and Render.

## Business model

Nirikkha is B2B SaaS with two revenue lines: monthly subscriptions and paid reports beyond the plan limits.

| Plan                      | For                                                                   | Includes                                                                                                   | Price (proposed)       |
| ------------------------- | --------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------- | ---------------------- |
| Free                      | Students, individual investors, trial                                 | 3 Crash-Tests per month, short report, evidence links                                                      | $0                     |
| Analyst Pro               | Individual analysts, small funds                                      | 30 Crash-Tests per month, full evidence and Rule Engine results, PDF export, Radar alerts for 10 companies | $49 per user per month |
| Team                      | Research and compliance teams (up to 5 users)                         | 150 Crash-Tests per month, shared workspace, decision workflow, audit trail, Radar for 50 companies        | $399 per month         |
| Enterprise                | Banks, institutional investors, large compliance departments          | Approved private documents, deployment on the customer's own servers, custom rules, SSO, unlimited use     | Annual contract        |
| Extra Crash-Test          | Beyond the plan limit                                                 | One report                                                                                                 | $19                    |
| Deep Investigation Report | Multi-year, cross-document, Replay-style analysis, approval-ready PDF | One report                                                                                                 | $199                   |

Prices are a first proposal and will be finalised with pilot customers.

**First customers:** investment research teams, mid-size asset managers and funds that already read 10-K and proxy filings before investing or partnering. Second wave: corporate compliance teams and internal auditors (the Radar keeps them coming back), and bank credit and KYC teams. Governance advisory and audit firms act as channel partners, because one firm runs many reports for its clients.

**Unit economics:** the rule engine, embeddings and reranking cost no tokens; cheap models handle simple steps and strong models only where needed; repeated analyses are cached. Each analysis logs its real tokens and cost; on free tiers the measured cost is $0.00 per Crash-Test (for example 5 LLM calls and 13,079 tokens for one Apple run).

**Payments:** no live payment in the prototype ("Start Free" and "Request a Pilot"). Later: an international card gateway, and for Bangladesh a merchant account with bKash, Nagad or a gateway such as SSLCommerz, never personal "send money".

**Go to market:** 0–6 months: five design partners use it free and give written feedback, target at least two letters of intent. 6–12 months: convert pilots to Analyst Pro and Team, sign the first advisory partner. After 12 months: Enterprise customers, new sources (UK Companies House, GLEIF) and international sales.

**Moat:** a growing record of verified Replays, a structured rules library per jurisdiction, a relationship graph that improves with every company analysed, trust from evidence-first and responsible-uncertainty design, and repeat usage because new filings and rule changes arrive every year.

## Market validation

Plan before submission: demo the product to two or three investment analysts or compliance professionals and collect written answers to three questions: how long a governance review takes them today, which part Nirikkha would help with, and what price they would pay. Results will be added here as received, without changing their words.

## Global readiness and scalability

Modular design: ingestion sources, rule packs and model routes are separate modules, so a new jurisdiction means a new source and a new rule pack, not a rewrite. The API is stateless with a job queue, so more workers scale analysis. An Enterprise install runs the same services on the customer's servers with Private mode. The interface and memos are bilingual (English and Bengali) and the text layer is ready for more languages.

## Responsible AI

Every finding is cited to page and passage; "Insufficient Evidence" is a first-class result; severity and confidence are separate; doubtful findings go to human review; Radar actions need human approval; personal data is redacted before any model call; Private mode fails closed; the Replay is protected against hindsight. Known limits and biases are documented in `docs/ETHICS.md`. Nirikkha never accuses a company of misconduct and is not legal or investment advice.
