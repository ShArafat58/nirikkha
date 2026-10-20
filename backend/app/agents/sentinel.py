"""AI Reliability Sentinel: checks every Crash-Test finding before it reaches the report.

Six checks (plan PDF, section 7):
  authoritative  every citation is a loaded SEC filing of this company, filed on or before the analysis date
  period         an analyst citation uses the latest filing of its form available at the analysis date
  sufficiency    no citation -> confidence cannot stay above "insufficient"; an analyst claim that something is
                 absent from the filings is only an excerpt-level observation
  contradiction  an analyst claim that a relationship does not exist conflicts with deterministic findings
  support        a different model (task "reason") judges whether the cited passages support each analyst claim
  human_review   set when any check warns or fails, or a high/critical finding rests on weak evidence

Deterministic findings are built from verified quotes or rule sentences, so the judge runs only on analyst findings.
The judge sees findings in small batches because reasoning models spend output tokens on hidden reasoning.
Risk severity is never changed. Evidence confidence can only go down, never up.

Run on a saved Crash-Test report:
    python -m app.agents.sentinel .cache/analyses/<file>.json
"""

from __future__ import annotations

import json
import re
import sys
from collections import Counter
from datetime import date
from pathlib import Path
from typing import Any, Callable

from app.llm.client import LLMError

PROMPT = Path(__file__).resolve().parent.parent / "prompts" / "sentinel_judge.v1.md"
CONFIDENCE_RANK = {"insufficient": 0, "low": 1, "medium": 2, "high": 3}
VERDICTS = ("verified", "needs_review", "downgraded", "unsupported")
MAX_QUOTE_CHARS = 700
MAX_CITES_JUDGED = 3
JUDGE_BATCH = 4
JUDGE_MAX_TOKENS = 1500
JUDGE_MAX_WAIT = 75   # seconds the router may wait for the per-minute token budget

ABSENCE = re.compile(
    r"\b(?:do|does|did)\s+not\s+(?:disclose|contain|provide|include|mention|show|report)\b"
    r"|\bnot\s+disclosed\b"
    r"|\bno\b[^.;]{0,100}\b(?:is|are|was|were)\s+(?:disclosed|provided|reported)\b",
    re.I,
)
NEGATION = re.compile(
    r"\bno\s+(?:disclosed\s+)?(?:relationships?|ties|related[- ]part\w*|transactions?|conflicts?|affiliations?)\b",
    re.I,
)


def _d(value: Any) -> date:
    return value if isinstance(value, date) else date.fromisoformat(str(value)[:10])


def _check(name: str, status: str, detail: str) -> dict:
    return {"check": name, "status": status, "detail": detail}


def _cap(confidence: str, cap: str) -> str:
    return confidence if CONFIDENCE_RANK[confidence] <= CONFIDENCE_RANK[cap] else cap


def latest_by_form(filings: list[dict], as_of: date) -> dict[str, dict]:
    latest: dict[str, dict] = {}
    for f in filings:
        d = _d(f["filing_date"])
        if d <= as_of and (f["form"] not in latest or d > _d(latest[f["form"]]["filing_date"])):
            latest[f["form"]] = f
    return latest


def deterministic_checks(finding: dict, filings_by_acc: dict[str, dict], latest: dict[str, dict], as_of: date,
                         all_findings: list[dict]) -> tuple[list[dict], list[str]]:
    """Checks that need no model. Returns (checks, confidence caps)."""
    checks: list[dict] = []
    caps: list[str] = []
    cites = finding.get("citations") or []
    llm = finding.get("source") == "llm"
    claim = finding.get("claim") or ""

    # 1. authoritative source + evidence freeze
    unknown = sorted({c.get("accession_no") or "?" for c in cites if c.get("accession_no") not in filings_by_acc})
    late = sorted({c["accession_no"] for c in cites if c.get("accession_no") in filings_by_acc
                   and _d(filings_by_acc[c["accession_no"]]["filing_date"]) > as_of})
    if unknown or late:
        parts = []
        if unknown:
            parts.append(f"not a loaded SEC filing of this company: {', '.join(unknown)}")
        if late:
            parts.append(f"filed after the analysis date {as_of}: {', '.join(late)}")
        checks.append(_check("authoritative", "fail", "Citation " + "; ".join(parts) + "."))
        caps.append("insufficient")
    elif cites:
        checks.append(_check("authoritative", "pass",
                             f"All citations are SEC filings of this company filed on or before {as_of}."))
    else:
        checks.append(_check("authoritative", "not_run", "No citation to check."))

    # 2. reporting period
    if not llm:
        checks.append(_check("period", "pass", "The deterministic investigation selects filings by date."))
    elif not cites:
        checks.append(_check("period", "not_run", "No citation to check."))
    else:
        newest_cited: dict[str, date] = {}
        for c in cites:
            f = filings_by_acc.get(c.get("accession_no"))
            if f:
                d = _d(f["filing_date"])
                newest_cited[f["form"]] = max(d, newest_cited.get(f["form"], d))
        stale = [f"{form} filed {d} (latest available: {_d(latest[form]['filing_date'])})"
                 for form, d in newest_cited.items() if form in latest and _d(latest[form]["filing_date"]) > d]
        if stale:
            checks.append(_check("period", "warn", "Relies on an older filing: " + "; ".join(stale)
                                 + ". Confirm the latest filing says the same."))
        else:
            checks.append(_check("period", "pass", "Uses the latest filing of each cited form."))

    # 3. enough evidence
    confidence = finding.get("evidence_confidence", "insufficient")
    if not cites and confidence != "insufficient":
        checks.append(_check("sufficiency", "fail", "No citation supports this finding."))
        caps.append("insufficient")
    elif llm and ABSENCE.search(claim):
        checks.append(_check("sufficiency", "warn",
                             "The claim says something is absent from the filings, but the analyst saw only excerpts. "
                             "Read it as 'not found in the reviewed passages'."))
        caps.append("low")
    elif not cites:
        checks.append(_check("sufficiency", "pass", "Reported openly as insufficient evidence."))
    else:
        checks.append(_check("sufficiency", "pass", f"{len(cites)} citation(s) attached."))

    # 4. contradictory evidence
    if llm and NEGATION.search(claim):
        ids = [f["id"] for f in all_findings
               if f.get("source") == "deterministic" and f.get("investigation") == "relationship"]
        if ids:
            checks.append(_check("contradiction", "fail",
                                 f"Claims no such relationship exists, but findings {', '.join(ids)} disclose "
                                 f"outside roles or related-party transactions."))
            caps.append("insufficient")
        else:
            checks.append(_check("contradiction", "pass", "Negative claim; no finding contradicts it."))
    else:
        checks.append(_check("contradiction", "pass", "No conflicting finding detected."))
    return checks, caps


def _judge_text(items: list[dict], filings_by_acc: dict[str, dict]) -> str:
    lines: list[str] = []
    for f in items:
        lines.append(f"### {f['id']}\nCLAIM: {f['claim']}")
        for i, c in enumerate(f["citations"][:MAX_CITES_JUDGED], 1):
            filing = filings_by_acc.get(c.get("accession_no"), {})
            form = c.get("form") or filing.get("form", "")
            filed = c.get("filing_date") or filing.get("filing_date", "?")
            quote = " ".join((c.get("quote") or "").split())[:MAX_QUOTE_CHARS]
            lines.append(f"EVIDENCE {i} ({form} filed {filed}, p.{c.get('page')}): {quote}")
    return "\n".join(lines)


def judge_support(findings: list[dict], complete: Callable[..., Any],
                  filings_by_acc: dict[str, dict]) -> tuple[dict[str, dict], list[dict], list[str]]:
    """Batched calls to the judge model for analyst findings with citations. Returns (verdicts, usage, errors)."""
    items = [f for f in findings if f.get("source") == "llm" and f.get("citations")]
    system = PROMPT.read_text(encoding="utf-8") if items else ""
    verdicts: dict[str, dict] = {}
    usages: list[dict] = []
    errors: list[str] = []
    for start in range(0, len(items), JUDGE_BATCH):
        batch = items[start:start + JUDGE_BATCH]
        messages = [{"role": "system", "content": system},
                    {"role": "user", "content": _judge_text(batch, filings_by_acc)}]
        try:
            r = complete("reason", messages, json_mode=True, max_tokens=JUDGE_MAX_TOKENS, max_wait=JUDGE_MAX_WAIT)
        except LLMError as exc:
            errors.append(f"batch {start // JUDGE_BATCH + 1}: {exc}"[:300])
            continue
        usages.append({"node": "sentinel", "provider": r.provider, "model": r.model, "input_tokens": r.input_tokens,
                       "output_tokens": r.output_tokens, "latency_ms": r.latency_ms, "cached": r.cached})
        data = r.data if isinstance(r.data, dict) else {}
        raw = data.get("verdicts") if isinstance(data.get("verdicts"), list) else []
        valid = {f["id"] for f in batch}
        for v in raw:
            if isinstance(v, dict) and v.get("id") in valid and v.get("supported") in ("yes", "partial", "no"):
                verdicts[v["id"]] = {"supported": v["supported"], "reason": str(v.get("reason", ""))[:300]}
    return verdicts, usages, errors


def review_findings(report: dict, facts: Any, complete: Callable[..., Any]) -> tuple[dict, list[dict]]:
    """Returns (new report with a `sentinel` block on every finding, usage records)."""
    as_of = _d(facts.as_of)
    filings_by_acc = {f["accession_no"]: f for f in facts.filings}
    latest = latest_by_form(facts.filings, as_of)
    findings = [dict(f) for f in report.get("findings", [])]
    verdicts, usages, errors = judge_support(findings, complete, filings_by_acc)

    for f in findings:
        checks, caps = deterministic_checks(f, filings_by_acc, latest, as_of, findings)
        if f.get("source") != "llm":
            checks.append(_check("support", "pass", "Deterministic finding built from verified quotes or rule evidence."))
        elif not f.get("citations"):
            checks.append(_check("support", "not_run", "No citation to judge."))
        elif f["id"] not in verdicts:
            checks.append(_check("support", "not_run", "Judge model unavailable or gave no verdict."))
        else:
            v = verdicts[f["id"]]
            if v["supported"] == "yes":
                checks.append(_check("support", "pass", v["reason"] or "Cited evidence supports the claim."))
            elif v["supported"] == "partial":
                checks.append(_check("support", "warn", v["reason"] or "Only part of the claim is supported."))
                caps.append("low")
            else:
                checks.append(_check("support", "fail", v["reason"] or "Cited evidence does not support the claim."))
                caps.append("insufficient")

        original = f["evidence_confidence"]
        confidence = original
        for cap in caps:
            confidence = _cap(confidence, cap)

        reasons = [c["check"] for c in checks if c["status"] in ("warn", "fail")]
        if f.get("source") == "llm" and any(c["check"] == "support" and c["status"] == "not_run" for c in checks):
            reasons.append("support not checked")
        if f["risk_severity"] in ("high", "critical") and CONFIDENCE_RANK[confidence] <= CONFIDENCE_RANK["low"]:
            reasons.append("severe risk on weak evidence")
        human = bool(reasons)
        checks.append(_check("human_review", "warn" if human else "pass",
                             "Human review needed: " + ", ".join(reasons) + "." if human else "No review trigger."))

        if any(c["check"] in ("authoritative", "contradiction", "support") and c["status"] == "fail" for c in checks):
            verdict = "unsupported"
        elif confidence != original:
            verdict = "downgraded"
        elif human:
            verdict = "needs_review"
        else:
            verdict = "verified"

        f["evidence_confidence"] = confidence
        f["sentinel"] = {"verdict": verdict, "human_review": human, "original_confidence": original, "checks": checks}

    counts = Counter(f["sentinel"]["verdict"] for f in findings)
    summary = {**report.get("summary", {}),
               "by_confidence": dict(Counter(f["evidence_confidence"] for f in findings)),
               "sentinel": {**{v: counts.get(v, 0) for v in VERDICTS},
                            "human_review": sum(1 for f in findings if f["sentinel"]["human_review"]),
                            "judged": len(verdicts), "judge_errors": errors,
                            "judge_model": usages[0]["model"] if usages else None}}
    old_usage = report.get("usage", {"llm_calls": 0, "input_tokens": 0, "output_tokens": 0, "cost_usd": 0.0, "calls": []})
    new_usage = {**old_usage, "calls": list(old_usage.get("calls", [])) + usages,
                 "llm_calls": old_usage.get("llm_calls", 0) + len(usages),
                 "input_tokens": old_usage.get("input_tokens", 0) + sum(u["input_tokens"] for u in usages),
                 "output_tokens": old_usage.get("output_tokens", 0) + sum(u["output_tokens"] for u in usages)}
    return {**report, "findings": findings, "summary": summary, "usage": new_usage}, usages


def _main(argv: list[str]) -> int:
    from app.llm.client import get_llm
    from app.rules.run import collect_facts

    if len(argv) != 2:
        print("usage: python -m app.agents.sentinel <saved report .json>")
        return 1
    path = Path(argv[1])
    report = json.loads(path.read_text(encoding="utf-8"))
    facts = collect_facts(report["cik"], date.fromisoformat(report["as_of"]))
    new, usages = review_findings(report, facts, get_llm().complete)

    print(f"== sentinel {new['summary']['sentinel']} ==")
    for u in usages:
        print(f"  judge call: {u['model']} in={u['input_tokens']} out={u['output_tokens']} {u['latency_ms']} ms cached={u['cached']}")
    for f in new["findings"]:
        s = f["sentinel"]
        conf = s["original_confidence"] if s["original_confidence"] == f["evidence_confidence"] else \
            f"{s['original_confidence']}->{f['evidence_confidence']}"
        flag = " HUMAN REVIEW" if s["human_review"] else ""
        print(f"\n  {f['id']:6} {s['verdict']:12} severity={f['risk_severity']:8} confidence={conf:20} {f['source']}{flag}")
        print(f"         {f['title'][:110]}")
        for c in s["checks"]:
            if c["status"] in ("warn", "fail") or (c["check"] == "support" and f["source"] == "llm"):
                print(f"         [{c['status']}] {c['check']}: {c['detail'][:200]}")
    out = path.with_name(path.stem + "_sentinel.json")
    out.write_text(json.dumps(new, indent=1, default=str), encoding="utf-8")
    print(f"\nsaved: {out}")
    return 0


if __name__ == "__main__":
    sys.exit(_main(sys.argv))