# Evaluation

Run: 2026-10-20 15:51 (Asia/Dhaka). Command: `python -m evaluation.run`. No LLM calls; cost $0.

These are small gold sets used as regression checks, not a statistical benchmark.

## Guardrails

- Prompt-injection heuristic: blocked **6/6** attacks, **0/6** false positives on normal decisions. Heuristic layer only; the attack set was written with knowledge of the patterns, so this result is optimistic. The safety model (gpt-oss-safeguard) runs after it in the live graph.
- PII redaction: caught **8/8** synthetic items (recall 100%); altered **0/6** public-filing sentences.

## Governance Rule Engine regression (SVB, evidence frozen 2023-03-10)

Result {'PASS': 11, 'POTENTIAL_GAP': 3} vs expected {'PASS': 11, 'POTENTIAL_GAP': 3}: **OK**.

## AI Reliability Sentinel (SVB deposit-partnership Crash-Test)

18 findings (7 from the analyst model). Judge openai/gpt-oss-120b gave a verdict on 6/7 analyst findings.
Verdicts: {'verified': 12, 'needs_review': 6, 'downgraded': 0, 'unsupported': 0}; 6 sent to human review.

Governance Health Score 42/100 (elevated_concern), evidence coverage 86%, 2 insufficient-evidence items listed separately.

## Legal memo citation checks

Status complete: 4 risks kept, 0 dropped (citation pass rate 1.0).
Flagged for legal review: 1 absence statements, 2 conduct-style rule wordings; 4 risks depend on human review.

## Measured earlier (build log)

- Governance extraction, SVB 2022 proxy: 162 relations proposed by the model, 137 verified against the source passage (85%); only verified relations enter the graph.
- Test suite: see `python -m pytest -q` (every module has unit tests with fake models; no network).
