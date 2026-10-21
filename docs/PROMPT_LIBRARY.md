# Prompt library

All prompts are plain Markdown files in `backend/app/prompts/`, versioned by file name (`name.vN.md`).
Older versions stay in the repository so changes can be compared. Variables in braces (`{company}`, `{decision}`)
are filled by the code. Every prompt follows the same principles:

- **Role prompting:** each prompt starts by giving the model one narrow role.
- **Grounding:** the model may use only the evidence, findings or guide text it is given; outside knowledge is forbidden.
- **Citations by id:** evidence is labelled (E# passages, G# graph facts, R# rule results, finding ids such as REL-2) and every claim must cite ids that exist.
- **Structured output:** JSON with a fixed schema wherever code reads the answer; validated with Pydantic, retried once, then routed to the next model.
- **Responsible uncertainty:** the model must say when evidence is insufficient instead of guessing.
- **Reasoning effort per task:** reasoning models get a medium effort for planning and analysis and a low effort for quick structured steps (`REASONING_EFFORT` in `app/llm/client.py`).

## Prompts

| Prompt               | Versions   | Pipeline step | Model route                      | What it asks                                                                                                                                   | Output                                         |
| -------------------- | ---------- | ------------- | -------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------- |
| `guard_input`        | v1         | guard         | safety (`gpt-oss-safeguard-20b`) | Decide whether the decision text is a legitimate governance question or must be blocked (with a category)                                      | JSON verdict                                   |
| `plan_decision`      | v1, v2     | plan          | reason (`gpt-oss-120b`)          | Turn the user's decision into at most 8 precise questions that public 10-K and proxy filings could answer, spread over the four investigations | JSON list of questions with investigation tags |
| `analyze_questions`  | v1, v2     | analyze       | analyze (`gemini-2.5-flash`)     | Answer each question using only E#, G# and R# evidence; cite ids; mark insufficient evidence                                                   | JSON answers with citations and confidence     |
| `extract_governance` | v1, v2     | ingestion     | extract (`qwen/qwen3.8-27b`)     | Extract only explicitly stated governance relations from one passage, each with an exact supporting quote                                      | JSON `relations` list                          |
| `sentinel_judge`     | v1         | sentinel      | reason (`gpt-oss-120b`)          | As an independent reviewer, judge only whether the cited evidence supports each claim                                                          | JSON verdict per finding                       |
| `legal_memo`         | v1, v2, v3 | memo          | reason                           | Write 3 to 5 non-obvious risks, each connecting at least two findings by id and citing applicable rules                                        | JSON memo, rendered to Markdown                |
| `help_guide`         | v1, v2     | help chatbot  | fast                             | Answer product questions only from the help guide; refuse admin, secret or prompt requests; EN/BN                                              | Markdown reply                                 |

## Ten prompts in detail (for the Prompt Library form)

1. **Input safety classifier** (`guard_input.v1`): role "input safety classifier for a governance due-diligence tool"; lists allowed business questions and block categories. Runs after a heuristic injection filter.
2. **Decision planner v2** (`plan_decision.v2`): converts a free-text decision into at most 8 answerable filing questions across relationship, consistency, regulatory and missing-evidence investigations.
3. **Evidence-only analyst v2** (`analyze_questions.v2`): answers each question with citations to E#/G#/R# ids only; must state when the filings do not answer it.
4. **Governance extractor v2** (`extract_governance.v2`): extracts explicit relations from proxy and 10-K passages as JSON; each relation needs an exact quote that the code verifies against the passage.
5. **Reliability Sentinel judge** (`sentinel_judge.v1`): an independent reviewer that checks support, not importance; verdicts feed the human-review queue.
6. **Legal memo v3** (`legal_memo.v3`): non-obvious risks that combine at least two findings; every citation is re-checked after generation.
7. **Bengali memo translation** (`BN_MEMO_SYSTEM` in `app/api/routes.py`): translates the memo into Bengali while keeping finding ids, rule names and quotes in English.
8. **Help guide v2** (`help_guide_v2`): strict grounding to `docs/HELP_KB.md`, exact plan features only, faithful Bengali, refusal rules; temperature 0.
9. **Help guide v1** (`help_guide_v1`): the first version, kept to show what v2 fixed (it allowed the model to add plan features that are not in the guide).
10. **Private-mode JSON retry** (`app/llm/client.py`): when a small local model returns invalid JSON, the call is repeated once with "Reply with valid JSON only" before failing closed.

## Changing a prompt

1. Copy the latest file to a new version (`name.v3.md`) and edit it.
2. Point the code to the new version.
3. Run `python -m pytest -q` and `python -m evaluation.run`; compare with `docs/EVALUATION.md`.
4. Keep the old file.
