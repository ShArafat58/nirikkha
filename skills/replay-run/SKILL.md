---
name: replay-run
description: Run, check and (only if better) publish a First Warning Sign Replay for a case such as SVB. Use when asked to re-run the Replay, compare a new Crash-Test with a replay case, or refresh the control comparison.
---

# Replay run

Goal: compare a Crash-Test with a documented case without hindsight, and publish only a result that is valid and at least as strong as the current one.

## Steps

1. **Check the case.** Read `backend/data/replay/<case>/case.json`. Note the freeze date. Never change the outcome text or the warning signs to fit a run.
2. **Make sure the run is new.** The same company, freeze date and decision return a cached report. To force a new run, change the decision wording slightly and say so in the notes.
3. **Run the Crash-Test** for the case company with the evidence freeze date set to the case freeze date (web app or `POST /api/crash-tests`). Wait until the job is `done`.
4. **Compare without publishing:**
   `cd backend` then `python -m app.replay.compare <case> --job <id-prefix>`
5. **Check the verdict.** It must be `VALID`. If it says INVALID, a citation is dated after the freeze: do not publish; investigate the leak.
6. **Decide.** Read `backend/data/replay/<case>/result.json` (the published run). Publish the new run only if it misses no more knowable signs and has no fewer detected + questioned signs. Otherwise keep the published run.
7. **Keep every run.** Copy the comparison from `backend/.cache/replay/` to `backend/data/replay/<case>/runs/` even when it is not published, so results are not cherry-picked.
8. **Publish (only if step 6 says so):** `python -m app.replay.compare <case> --job <id-prefix> --publish`
9. **Refresh the control** with a healthy company and the same kind of decision:
   `python -m app.replay.control <case> --subject <published-run> --control <control-run>`
10. **Update docs.** Record both runs and the control in `docs/REPLAY.md` with their numbers.
11. **Deploy.** Commit `backend/data/replay/`, push, and redeploy the backend (Render manual deploy).

## Rules

- Do not edit the case file to improve a result.
- Report "not knowable" signs honestly; they are not misses.
- Never publish a run whose verdict is not VALID.
