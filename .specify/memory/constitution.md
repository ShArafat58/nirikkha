<!--
Sync Impact Report:
- Version change: Initial adoption -> 1.0.0
- Principles defined:
  1. Evidence-First
  2. Responsible Uncertainty
  3. Separation of Risk Severity and Evidence Confidence
  4. Non-Accusatory Governance Language
  5. Strict Domain Separation (Law vs Best Practice vs Internal Indicators)
- Added sections:
  - Architecture and Technical Boundaries
  - Quality Gates and Development Workflow
  - Governance
- Follow-up TODOs: None
-->

# Nirikkha Constitution

## Core Principles

### I. Evidence-First
Every material finding, flag, or governance score MUST link directly to verifiable source evidence (SEC filing Form 10-K, DEF 14A, 8-K, or official regulation). Analysis without a verifiable citation, page/section number, and verbatim supporting passage is strictly prohibited. Unsubstantiated inferences or speculative leaps MUST NOT enter crash-test reports.

### II. Responsible Uncertainty
When evidence is incomplete, contradictory, ambiguous, or missing, the system MUST report "Insufficient Evidence" rather than extrapolate or hypothesize. Hallucinating missing disclosures or guessing compliance status violates Nirikkha's core mandate: "Trust less, Verify more."

### III. Separation of Risk Severity and Evidence Confidence
Risk Severity (the operational or legal impact of an issue) and Evidence Confidence (the clarity and reliability of supporting disclosures) MUST always remain separate, distinct attributes. A severe risk with weak documentation MUST NOT be conflated with a well-documented minor discrepancy.

### IV. Non-Accusatory Governance Language
Nirikkha produces objective risk analyses, not accusations. Findings MUST describe factual patterns and potential conflicts requiring review or remediation. The system MUST NEVER accuse a company, officer, or board member of illegal conduct, fraud, or intentional wrongdoing. Relationships are cataloged as "potential conflicts requiring review," never as proof of misconduct.

### V. Strict Domain Separation
Applicable statutory law (e.g., SEC Item 401, Item 404, Item 407, Sarbanes-Oxley), industry best practices (e.g., independent board leadership, tenure recommendations), and internal corporate risk indicators MUST be categorized separately in all analyses and interfaces. Best-practice suggestions MUST NEVER be labeled as legal violations.

## Architecture and Technical Boundaries

### Frontend and Backend Isolation
- Frontend and backend MUST share no code. Communication occurs exclusively through the documented REST API contracts in `docs/API.md`.
- The frontend reads the backend URL solely from `NEXT_PUBLIC_API_URL` and MUST maintain a functional mock mode for disconnected evaluation.
- Any change to an API response contract MUST be reflected simultaneously in `docs/API.md`.

### Security, Zero Secrets, and Free Stack
- No API keys, credentials, or secrets are ever checked into git. All environment secrets reside in `.env` (git-ignored) with an up-to-date `.env.example`.
- Nirikkha adheres to a 100% free stack. Integrations requiring paid plans or closed proprietary APIs are prohibited.
- LLM calls MUST route through a resilient router with graceful fallbacks (Groq -> Gemini -> local Ollama). The system must never crash on provider downtime.

### Data Privacy and Public Sources
- Demo and replay data MUST strictly utilize public SEC filings or synthetic data. Under no circumstances should non-public personal information be processed or exposed.
- SEC EDGAR access MUST adhere strictly to SEC fair-access policies: always include a identifying User-Agent header with email, and honor rate limits.

## Quality Gates and Development Workflow

### Dual-Language Accessibility (EN/BN)
Every user-facing string, button label, notification, modal, error message, and report element MUST be localized in both English (EN) and Bengali (BN) through the central i18n dictionary. No hardcoded user-facing English strings are permitted in UI components.

### Tests Before Merge
- Code changes MUST be accompanied by verification tests (`pytest` for backend, build and test checks for frontend).
- Every external integration MUST include robust error handling with user-friendly messages for rate limits, network failures, or unreadable inputs.
- Analyses MUST be cached in the database; demo companies and First Warning Sign Replays are precomputed.
- Never claim any feature in documentation or submission materials that is not fully implemented and visible in this repository.

## Governance

This Constitution supersedes all informal team practices, local conventions, and transient directives. All code reviews, specs, and feature pull requests MUST verify compliance with these principles before merge. Any amendment to this Constitution requires explicit documentation, version bump, and architectural alignment.

**Version**: 1.0.0 | **Ratified**: 2026-10-22 | **Last Amended**: 2026-10-22
