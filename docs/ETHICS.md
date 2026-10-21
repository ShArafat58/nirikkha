# Responsible AI, safeguards and limitations

Nirikkha helps people ask better questions before a decision. It is not built to accuse anyone,
and it is not legal or investment advice.

## 1. Principles built into the product

| Principle                  | How it is enforced                                                                                                                                                        |
| -------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Evidence first             | No material finding without a citation to filing, page, section and quote; the Sentinel and the memo citation check remove unsupported claims                             |
| Responsible uncertainty    | "Insufficient Evidence" is a first-class result in the rule engine, the analyst prompt and the report; it is listed separately and never counted as low risk              |
| Severity is not confidence | Risk Severity and Evidence Confidence are separate fields on every finding, so a serious but weakly evidenced concern is not shown as proven                              |
| No accusation              | Relationships are labelled "potential conflict requiring review"; prompts forbid misconduct claims; the help chatbot refuses to call any company guilty                   |
| Law vs best practice       | Every rule states whether it is applicable law, best practice or an internal risk indicator; sector-specific rules are marked not applicable with a reason                |
| Human in the loop          | Findings the Sentinel does not verify go to a human-review queue; Radar follow-up actions start only after a person approves; decisions are stored with reviewer and time |
| No hindsight               | The Replay freezes evidence at a date and marks a run invalid if any citation is dated after it                                                                           |

## 2. Safeguards

| Risk                        | Safeguard                                                                                                                                                    |
| --------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| Personal data in user text  | PII redaction before any model call (emails, phones, ID and card numbers); tested 8/8 caught, 0/6 false changes                                              |
| Prompt injection            | Heuristic filter, then the `gpt-oss-safeguard-20b` safety model; the chatbot refuses requests for prompts, secrets or admin data                             |
| Hallucinated facts          | Retrieval-only answers with evidence ids, quote verification for graph relations, Sentinel judge, memo citation re-check, temperature 0 for the help chatbot |
| Confidential documents      | Private mode runs all AI steps on local models and fails closed instead of using the cloud                                                                   |
| Data leaks from the chatbot | No database, user or admin modules imported (tested); replies redacted; per-client rate limit                                                                |
| Account security            | argon2id hashing, short admin sessions with a step-up, masked reviewer emails                                                                                |
| Secrets                     | Only in git-ignored `.env` files and host secret settings                                                                                                    |

## 3. Known biases and limitations

- **Coverage bias:** only U.S. SEC filings in English for now. Companies with thinner disclosure get more "Insufficient Evidence", which is honest but can make them look riskier at a glance.
- **Disclosure is not conduct:** filings show the oversight structure, not whether it worked. The Replay marks this ("the board did not manage risks" is only _questioned_, not _detected_).
- **Model behaviour:** LLM answers vary between runs. Two independent SVB runs gave Health 68 and 58; both were VALID with no missed knowable sign, but one sign moved from _questioned_ to _partial_.
- **Small local models are less critical:** the same Apple decision scored 87 with cloud models and 94 in Private mode.
- **Case selection:** the Replay uses one well-known failure (SVB) and one control (Apple). That shows the method works on a documented case; it does not prove general predictive accuracy.
- **Not knowable from public data:** confidential supervisory findings at SVB could not be seen in filings; the Replay reports this as _not knowable_ rather than missed.
- **Translation:** Bengali output is machine-translated; ids, rule names and quotes stay in English to avoid changing meaning.
- **Extraction errors:** table layouts can be misread (for example a committee matrix); only quote-verified relations enter the graph, and table rows must name their committee.

## 4. Measurable KPIs

| KPI                          | Current value                                                          | Source                                  |
| ---------------------------- | ---------------------------------------------------------------------- | --------------------------------------- |
| Retrieval hit@1 / MRR        | 90% / 0.933 on 10 gold questions                                       | `docs/EVALUATION.md`                    |
| Extraction precision proxy   | 85% of proposed relations verified against the source quote (SVB 2022) | `docs/EVALUATION.md`                    |
| Memo citation pass rate      | 1.0 (4 of 4 risks kept)                                                | `docs/EVALUATION.md`                    |
| Sentinel outcome             | 12 verified, 6 needs review, 0 unsupported (SVB run)                   | `docs/EVALUATION.md`                    |
| Replay knowable signs caught | 5 of 5 detected or questioned; 0 missed (run 07da9556)                 | `docs/REPLAY.md`                        |
| Control separation           | SVB 68 vs Apple 85 Health; Apple misses 2 of 5 signs                   | `backend/data/replay/svb/controls.json` |
| Injection blocking           | 6/6 blocked, 0/6 false positives (optimistic, heuristic layer)         | `docs/EVALUATION.md`                    |

## 5. Intended use

Due-diligence support for investment analysts, compliance teams, internal auditors, banks and advisory firms.
Every output is a starting point for human verification. Users are asked not to enter personal or confidential
information in the public version; confidential work belongs in Private mode or an Enterprise install.
