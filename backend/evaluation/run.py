"""Nirikkha evaluation suite. No LLM calls: costs $0.

    python -m evaluation.run            # everything (retrieval needs Supabase + local models)
    python -m evaluation.run --offline  # skip retrieval

Writes evaluation/results.json and docs/EVALUATION.md.
"""

from __future__ import annotations

import argparse
import glob
import json
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

from app.agents.graph import INJECTION
from app.agents.memo import ABSENCE as _A  # noqa: F401  (same regex the memo uses)
from app.guardrails.pii import redact_pii
from evaluation.gold import (BENIGN, EXPECTED_SVB_RULES, INJECTIONS, PII_NEGATIVE, PII_POSITIVE, RETRIEVAL)

ROOT = Path(__file__).resolve().parent.parent
ANALYSES = ROOT / ".cache" / "analyses"
DOCS = ROOT.parent / "docs" / "EVALUATION.md"


def _text(hit) -> str:
    data = hit.model_dump(mode="json") if hasattr(hit, "model_dump") else dict(hit)
    return " ".join(str(v) for v in data.values() if isinstance(v, str))


def eval_retrieval() -> dict:
    from app.rag.retrieve import retrieve

    rows, ranks = [], []
    started = time.perf_counter()
    for question, cik, as_of, expect in RETRIEVAL:
        hits, _ = retrieve(question, k=3, cik=cik, before=as_of + timedelta(days=1))
        rank = next((i for i, h in enumerate(hits, 1) if any(e.lower() in _text(h).lower() for e in expect)), None)
        ranks.append(rank)
        rows.append({"question": question, "cik": cik, "as_of": as_of.isoformat(), "expect": expect, "rank": rank})
    n = len(ranks)
    return {"n": n, "hit_at_1": round(sum(r == 1 for r in ranks) / n, 3),
            "hit_at_3": round(sum(r is not None for r in ranks) / n, 3),
            "mrr": round(sum(1 / r for r in ranks if r) / n, 3),
            "seconds": round(time.perf_counter() - started, 1), "rows": rows}


def eval_injection() -> dict:
    blocked = [bool(INJECTION.search(t)) for t in INJECTIONS]
    false_pos = [bool(INJECTION.search(t)) for t in BENIGN]
    return {"attacks": len(INJECTIONS), "blocked": sum(blocked), "benign": len(BENIGN),
            "false_positives": sum(false_pos),
            "missed": [t for t, b in zip(INJECTIONS, blocked) if not b],
            "note": ("Heuristic layer only; the attack set was written with knowledge of the patterns, so this result is optimistic. "
                     "The safety model (gpt-oss-safeguard) runs after it in the live graph.")}


def eval_pii() -> dict:
    caught, missed = 0, []
    for text, label in PII_POSITIVE:
        _, counts = redact_pii(text)
        if counts.get(label):
            caught += 1
        else:
            missed.append(text)
    altered = [t for t in PII_NEGATIVE if redact_pii(t)[0] != t]
    return {"positives": len(PII_POSITIVE), "caught": caught, "recall": round(caught / len(PII_POSITIVE), 3),
            "negatives": len(PII_NEGATIVE), "false_positives": len(altered), "missed": missed, "altered": altered}


def _latest(pattern: str) -> Path | None:
    files = sorted(glob.glob(str(ANALYSES / pattern)), key=lambda p: Path(p).stat().st_mtime)
    return Path(files[-1]) if files else None


def eval_reports() -> dict:
    out: dict = {}
    sp = _latest("0000719739_*_sentinel.json")
    if sp:
        rep = json.loads(sp.read_text(encoding="utf-8"))
        rules = rep["rule_report"]["summary"]["by_result"]
        llm = [f for f in rep["findings"] if f.get("source") == "llm"]
        s = rep["summary"]["sentinel"]
        out["rules"] = {"svb_by_result": rules, "expected": EXPECTED_SVB_RULES, "regression_ok": rules == EXPECTED_SVB_RULES}
        out["sentinel"] = {"file": sp.name, "findings": len(rep["findings"]), "llm_findings": len(llm),
                           "judged": s.get("judged"), "verdicts": {k: s[k] for k in ("verified", "needs_review", "downgraded", "unsupported")},
                           "human_review": s["human_review"], "judge_model": s.get("judge_model")}
        from app.agents.score import health_score
        h = health_score(rep)
        out["health"] = {"score": h["score"], "band": h["band"], "coverage_pct": h["coverage"]["pct"],
                         "insufficient": h["insufficient_evidence"]["count"]}
    mp = _latest("0000719739_*_memo.json")
    if mp:
        memo = json.loads(mp.read_text(encoding="utf-8"))
        risks = memo.get("risks", [])
        proposed = len(risks) + len(memo.get("dropped", []))
        out["memo"] = {"file": mp.name, "status": memo.get("status"), "risks_kept": len(risks),
                       "risks_dropped": len(memo.get("dropped", [])),
                       "citation_pass_rate": round(len(risks) / proposed, 3) if proposed else None,
                       "absence_flagged": sum(bool(r.get("absence_claim")) for r in risks),
                       "rule_wording_flagged": sum(bool(r.get("rule_wording")) for r in risks),
                       "needs_human_review": sum(bool(r.get("needs_human_review")) for r in risks)}
    return out


def to_markdown(res: dict) -> str:
    L = ["# Evaluation", "", f"Run: {res['run_at']} (Asia/Dhaka). Command: `python -m evaluation.run`. No LLM calls; cost $0.",
         "", "These are small gold sets used as regression checks, not a statistical benchmark.", ""]
    r = res.get("retrieval")
    if r:
        L += ["## Retrieval (hybrid pgvector + full-text, RRF, cross-encoder rerank, evidence frozen at analysis date)", "",
              f"{r['n']} gold questions: **hit@1 {r['hit_at_1']:.0%}**, **hit@3 {r['hit_at_3']:.0%}**, MRR {r['mrr']}, {r['seconds']} s total.", "",
              "| Question | Company | Rank of first correct passage |", "|---|---|---|"]
        L += [f"| {x['question']} | {'SVB' if x['cik'].endswith('719739') else 'Apple'} | {x['rank'] or 'not in top 3'} |" for x in r["rows"]]
        L.append("")
    i, p = res["injection"], res["pii"]
    L += ["## Guardrails", "",
          f"- Prompt-injection heuristic: blocked **{i['blocked']}/{i['attacks']}** attacks, **{i['false_positives']}/{i['benign']}** false positives on normal decisions. {i['note']}",
          f"- PII redaction: caught **{p['caught']}/{p['positives']}** synthetic items (recall {p['recall']:.0%}); altered **{p['false_positives']}/{p['negatives']}** public-filing sentences.",
          ""]
    rep = res.get("reports", {})
    if "rules" in rep:
        x = rep["rules"]
        L += ["## Governance Rule Engine regression (SVB, evidence frozen 2023-03-10)", "",
              f"Result {x['svb_by_result']} vs expected {x['expected']}: **{'OK' if x['regression_ok'] else 'CHANGED'}**.", ""]
    if "sentinel" in rep:
        s = rep["sentinel"]
        L += ["## AI Reliability Sentinel (SVB deposit-partnership Crash-Test)", "",
              f"{s['findings']} findings ({s['llm_findings']} from the analyst model). Judge {s['judge_model']} gave a verdict on {s['judged']}/{s['llm_findings']} analyst findings.",
              f"Verdicts: {s['verdicts']}; {s['human_review']} sent to human review.", ""]
    if "health" in rep:
        h = rep["health"]
        L += [f"Governance Health Score {h['score']}/100 ({h['band']}), evidence coverage {h['coverage_pct']}%, {h['insufficient']} insufficient-evidence items listed separately.", ""]
    if "memo" in rep:
        m = rep["memo"]
        L += ["## Legal memo citation checks", "",
              f"Status {m['status']}: {m['risks_kept']} risks kept, {m['risks_dropped']} dropped (citation pass rate {m['citation_pass_rate']}).",
              f"Flagged for legal review: {m['absence_flagged']} absence statements, {m['rule_wording_flagged']} conduct-style rule wordings; {m['needs_human_review']} risks depend on human review.", ""]
    L += ["## Measured earlier (build log)", "",
          "- Governance extraction, SVB 2022 proxy: 162 relations proposed by the model, 137 verified against the source passage (85%); only verified relations enter the graph.",
          "- Test suite: see `python -m pytest -q` (every module has unit tests with fake models; no network)."]
    return "\n".join(L) + "\n"


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--offline", action="store_true")
    args = ap.parse_args(argv[1:])
    res = {"run_at": datetime.now().strftime("%Y-%m-%d %H:%M"), "injection": eval_injection(), "pii": eval_pii(),
           "reports": eval_reports()}
    if not args.offline:
        res["retrieval"] = eval_retrieval()
    (ROOT / "evaluation" / "results.json").write_text(json.dumps(res, indent=1, default=str), encoding="utf-8")
    DOCS.write_text(to_markdown(res), encoding="utf-8")
    print(to_markdown(res))
    print(f"saved: {DOCS}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))