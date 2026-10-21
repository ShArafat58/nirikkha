# First Warning Sign Replay: Silicon Valley Bank

Question: using only what was public **before** the failure, would Nirikkha have raised the right governance questions?
This is a historical test of usefulness, not a claim that the system predicts crises.

## The five steps

| Step                              | What we did                                                                                                                                     | Where                                                  |
| --------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------ |
| 1. Establish the timeline         | 12 dated events from public sources. Each event has two dates: when it happened and when it became public                                       | `backend/data/replay/svb/case.json`                    |
| 2. Reconstruct the evidence       | Filings public before the freeze: 10-K for 2021 and 2022, DEF 14A for 2021 and 2022, PRE 14A filed 3 March 2023                                 | Supabase + Neo4j                                       |
| 3. Freeze the evidence            | Freeze date **7 March 2023**, three days before the closure. Retrieval, graph facts and rules only see items public on or before that date      | `app/replay/case.py` (`is_visible`, `evidence_window`) |
| 4. Run Nirikkha                   | Decision: "Before we proceed with a deposit partnership with this bank, identify the governance risks and evidence gaps we should investigate." | Run `07da9556`                                         |
| 5. Compare with the known outcome | Each documented warning sign is scored against the report; a leak check makes the run INVALID if any citation is dated after the freeze         | `app/replay/compare.py`                                |

Known outcome: Silicon Valley Bank was closed by the California DFPI on 10 March 2023 and the FDIC was appointed receiver.
The Federal Reserve's review (28 April 2023) found that the board and management did not manage the bank's risks effectively.

## Result (published: run 07da9556)

**Verdict: VALID** (no citation after the freeze date). Health Score 68 (moderate concern), evidence coverage 81%.

| Warning sign                                                           | Status           | How the report raised it                                                            |
| ---------------------------------------------------------------------- | ---------------- | ----------------------------------------------------------------------------------- |
| Large, long-duration securities portfolio exposed to rising rates      | **detected**     | Year-over-year change in market-risk disclosure (rule II_YOY_CHANGE, Potential Gap) |
| Chief Risk Officer role without a permanent holder for most of 2022    | **detected**     | Risk-leadership change rule (II_RISK_LEADERSHIP_CHANGE, Potential Gap)              |
| Deposits concentrated in one sector and mostly above the insured limit | **questioned**   | Decision question on liquidity and risk oversight                                   |
| Board and management did not manage risks effectively                  | **questioned**   | Filings show the oversight structure, not whether it worked                         |
| Executive incentives not tied to risk outcomes                         | **questioned**   | Compensation-metric question (return on equity, earnings per share)                 |
| Many open confidential supervisory findings                            | **not knowable** | Confidential; not in public filings                                                 |

Detected 2, questioned 3, missed 0, not knowable 1 → all 5 knowable signs raised as a finding or an open question.

Statuses: _detected_ = a finding states the issue with evidence; _questioned_ = the report raises it as an open question;
_partial_ = touched but incomplete; _missed_ = not raised; _not knowable_ = not in public data.

## Reproducibility: a second independent run

Run `6ddec5af` (same freeze date, same decision with one word added so the cache was not reused):
**VALID**, Health 58, detected 2, questioned 2, **partial 1** (deposit concentration), missed 0, not knowable 1.
Both runs raise every knowable sign; one sign is weaker in the second run. File: `backend/data/replay/svb/runs/second_run_6ddec5af.json`.
We publish the first run and show the second, so the result is not one lucky run.

## Control: does it flag everyone?

Apple Inc., same kind of decision ("Before we proceed with a partnership with this company…"), run `cc5cdb6c`:

|                         | Health      | Coverage | Detected | Questioned | Partial | Missed |
| ----------------------- | ----------- | -------- | -------- | ---------- | ------- | ------ |
| SVB (frozen 2023-03-07) | 68 moderate | 81%      | 2        | 3          | 0       | 0      |
| Apple (control)         | 85 low      | 80%      | 1        | 1          | 1       | 2      |

Apple scores higher and misses two of the SVB-type signs, so Nirikkha does not raise the same alarms for every company.
Caveat: we have no Apple filings from before 2023, so the control uses Apple's current filings.

## Avoiding hindsight bias

- Every case event stores its public date; anything later is invisible to the run.
- The leak check scans citations and fails the run if one is dated after the freeze.
- The run date guard refuses to compare a run whose analysis date is after the freeze.
- Outcome text is used only in step 5, never given to the models.
- Signs that needed confidential data are reported as not knowable instead of being counted as misses.

## Reproduce it

```powershell
cd backend
python -m app.replay.compare svb --job 07da9556            # compare a run with the case
python -m app.replay.compare svb --job <id> --publish      # also write data/replay/svb/result.json
python -m app.replay.control svb --subject 07da9556 --control cc5cdb6c
```

The `/replay` page shows the timeline, the freeze strip, each warning sign with its evidence, and the control comparison, in English and Bengali.
