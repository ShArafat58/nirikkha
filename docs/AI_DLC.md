# AI-assisted development lifecycle (AI-DLC)

How AI coding agents were used to build Nirikkha, and the rules that kept them safe and reviewable.

## Frameworks used

| Framework       | What it is                                                                 | How we used it                                                                                                                                                                 | Evidence                                                           |
| --------------- | -------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | ------------------------------------------------------------------ |
| AGENTS.md       | A context file every coding agent reads first                              | Product principles (evidence first, Insufficient Evidence, severity vs confidence, no accusations), repo layout, who edits what, secrets rules, test rules                     | `AGENTS.md`                                                        |
| GitHub Spec Kit | Spec-driven development: constitution → specify → plan → tasks → implement | Initialised with the Gemini integration and PowerShell scripts; feature 001 (report share link and JSON export) went through every step and was implemented from its task list | `.specify/`, `.gemini/commands/`, `specs/001-report-share-export/` |
| Agent Skills    | A `SKILL.md` with step-by-step instructions an agent loads for one job     | `replay-run`: re-run, check and publish a Replay without hindsight or cherry-picking                                                                                           | `skills/replay-run/SKILL.md`                                       |

## Process

1. **Context first.** Agents start from `AGENTS.md` and, for new features, the Spec Kit constitution, which repeats the same principles.
2. **One small step at a time.** Each step has a goal, the files it touches, and a test. Large changes are split; an agent never edits frontend and backend in one undocumented sweep.
3. **Tests and builds before merge.** `python -m pytest -q` (234 tests, fake models, no network) and `npm run build` must pass. New behaviour gets a test (for example private mode fails closed, the help chatbot never imports database or auth modules).
4. **Human review of every AI output.** Code from agents and from UI builders is read before merging. Review caught real problems: a Bolt.new component spread an array into an object (runtime crash), the help chatbot invented an Enterprise "dedicated support" feature (fixed with a stricter prompt and temperature 0), and a rate limit keyed on the proxy IP would have blocked all users at once.
5. **Versioned prompts.** Prompts are files (`backend/app/prompts/*.vN.md`); old versions are kept.
6. **Honest records.** Replay runs are all kept, not only the best one; limits are written down in `docs/ETHICS.md`.

## Skill use log

| Date        | Skill                  | Request                             | Result                                                                                                                                                                                                                                |
| ----------- | ---------------------- | ----------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 22 Oct 2026 | replay-run (steps 4–7) | Check the second SVB run `6ddec5af` | Verdict VALID; detected 2, questioned 2, partial 1, missed 0. Decision: **do not publish** — the published run `07da9556` raises 5 knowable signs as detected or questioned, this run 4. Run kept in `backend/data/replay/svb/runs/`. |

## Spec Kit feature log

| Feature                               | Artifacts                                                                                                                                      | Implementation                                                   |
| ------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------- |
| 001 Report share link and JSON export | `spec.md`, `plan.md`, `research.md`, `data-model.md`, `contracts/report-actions.md`, `quickstart.md`, `tasks.md`, `checklists/requirements.md` | `frontend/src/components/report/report-actions.tsx`, report page |
