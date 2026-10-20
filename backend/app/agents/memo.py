"""Legal memo (Legal Copilot): a Crash-Test report turned into a memo with 3-5 non-obvious risks.

The memo model (task "reason") sees only findings the Reliability Sentinel kept (verified / needs_review, not
insufficient) and the Reg S-K rules evaluated in the report. Code then verifies every citation:
  - each risk must connect at least two known finding ids (the combination is what makes it non-obvious)
  - each risk must cite at least one rule exactly as it appears in the rule report
  - unknown ids are removed and recorded; risks that fail are dropped and recorded
  - fewer than 3 surviving risks -> status "insufficient" (no padding)
Evidence gaps, the score snapshot and the disclaimer are written by code, not by the model.

Run on a saved report:
    python -m app.agents.memo .cache/analyses/<file>_sentinel.json
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any, Callable

from app.agents.report import _citation
from app.agents.sentinel import ABSENCE
from app.llm.client import LLMError

PROMPT = Path(__file__).resolve().parent.parent / "prompts" / "legal_memo.v3.md"
MIN_RISKS = 3
MAX_RISKS = 5
ELIGIBLE_VERDICTS = ("verified", "needs_review")
SEVERITIES = ("low", "medium", "high", "critical")
SEVERITY_RANK = {s: i for i, s in enumerate(SEVERITIES)}
MAX_QUOTE_CHARS = 300
LOADED = re.compile(r"\b(?:conceal\w*|hid(?:e|es|den|ing)|mislead\w*|deceiv\w*|decept\w*|fraud\w*|cover[- ]?ups?|manipulat\w*)\b", re.I)
RULE_MEANING = {
    "Reg S-K Item 401(a)": "requires disclosure of each director's name, age and positions",
    "Reg S-K Item 401(e)(2)": "requires disclosure of other public-company directorships each director held in the past five years",
    "Reg S-K Item 402(c)": "requires the Summary Compensation Table for named executive officers",
    "Reg S-K Item 402(v)": "requires the pay-versus-performance disclosure",
    "Reg S-K Item 404(a)": "requires disclosure of transactions above $120,000 in which a related person had a material interest; a 10-K usually incorporates this disclosure from the proxy by reference (Part III, Item 13), so its absence from the 10-K text is not an inconsistency",
    "Reg S-K Item 404(b)": "requires disclosure of the company's policies and procedures for reviewing related-person transactions, if any",
    "Reg S-K Item 407(a)": "requires disclosure of which directors are independent",
    "Reg S-K Item 407(d)(5)": "requires disclosure of whether the audit committee has an audit committee financial expert",
    "Reg S-K Item 407(h)": "requires disclosure of the board leadership structure and the board's role in risk oversight",
}
RULE_WORDING = re.compile(r"\b(?:Item\s+\d{3}\S*|rule)\s+(?:mandates?|obligates?|requires\s+(?!disclosure|the\s+disclosure|companies\s+to\s+disclose)\w+)|\b(?:as\s+)?required\s+by\s+(?:Reg\S*\s+S-K\s+)?Items?\s+\d{3}", re.I)
DISCLAIMER = ("AI-generated draft for internal review; not legal advice. Every risk cites findings and rules that were "
              "checked against the Crash-Test report. Findings marked for human review must be confirmed before "
              "relying on any conclusion that depends on them.")


def eligible_findings(report: dict) -> list[dict]:
    return [f for f in report.get("findings", [])
            if (f.get("sentinel") or {}).get("verdict") in ELIGIBLE_VERDICTS
            and f.get("evidence_confidence") != "insufficient"]


def allowed_rules(report: dict) -> list[str]:
    return sorted({str(r.get("source")) for r in (report.get("rule_report") or {}).get("results", [])
                   if str(r.get("source", "")).startswith("Reg S-K")})


def build_pack(report: dict, findings: list[dict], rules: list[str]) -> str:
    lines = [f"Company: {report.get('company')}", f"Analysis date: {report.get('as_of')}",
             f"Decision: {report.get('decision') or '(general crash-test)'}"]
    h = report.get("health")
    if h:
        lines.append(f"Governance Health Score: {h['score']}/100 ({h['band']}), evidence coverage {h['coverage']['pct']}%")
    lines.append("\nFINDINGS (cite by id):")
    for f in findings:
        s = f.get("sentinel") or {}
        lines.append(f"[{f['id']}] severity={f['risk_severity']} confidence={f['evidence_confidence']} "
                     f"investigation={f['investigation']} review={'needs_review' if s.get('human_review') else 'verified'}")
        lines.append(f"  title: {f['title']}")
        lines.append(f"  claim: {f['claim']}")
        notes = [c['detail'] for c in s.get('checks', []) if c.get('status') in ('warn', 'fail') and c.get('check') != 'human_review']
        if notes:
            lines.append('  reviewer notes: ' + ' | '.join(n[:160] for n in notes))
        if f.get("citations"):
            c = f["citations"][0]
            quote = " ".join((c.get("quote") or "").split())[:MAX_QUOTE_CHARS]
            lines.append(f"  evidence: {c.get('form') or ''} {c.get('accession_no')} p.{c.get('page')}: \"{quote}\"")
    lines.append("\nRULES (cite exactly as written):")
    by_source: dict[str, list[str]] = {}
    for r in (report.get("rule_report") or {}).get("results", []):
        if r.get("source") in rules:
            by_source.setdefault(r["source"], []).append(f"{r.get('title')}: {r.get('result')}")
    for rule in rules:
        lines.append(f"- {rule}: {RULE_MEANING.get(rule, 'a disclosure requirement')} (results: {'; '.join(by_source.get(rule, []))})")
    return "\n".join(lines)


def validate_risks(data: Any, by_id: dict[str, dict], rules: list[str], cik: str) -> tuple[list[dict], list[str]]:
    risks: list[dict] = []
    dropped: list[str] = []
    raw = data.get("risks") if isinstance(data, dict) and isinstance(data.get("risks"), list) else []
    for i, r in enumerate(raw, 1):
        if not isinstance(r, dict):
            continue
        title = str(r.get("title", "")).strip()[:160] or f"Risk {i}"
        given = [x for x in r.get("finding_ids", []) if isinstance(x, str)] if isinstance(r.get("finding_ids"), list) else []
        ids = list(dict.fromkeys(x for x in given if x in by_id))
        removed = sorted(set(given) - set(ids))
        given_rules = r.get("rules") if isinstance(r.get("rules"), list) else []
        cited_rules = list(dict.fromkeys(x for x in given_rules if x in rules))
        if len(ids) < 2:
            dropped.append(f"{title}: needs at least two verified findings (valid: {', '.join(ids) or 'none'})")
            continue
        if not cited_rules:
            dropped.append(f"{title}: no rule from the evaluated Reg S-K list (given: {', '.join(map(str, given_rules)) or 'none'})")
            continue
        text = ' '.join(str(r.get(k, '')) for k in ('title', 'analysis', 'why_non_obvious', 'recommended_action'))
        loaded = sorted({m.group(0).lower() for m in LOADED.finditer(text)})
        if loaded:
            dropped.append(f"{title}: wording implies intent ({', '.join(loaded)})")
            continue
        severity = r.get("severity") if r.get("severity") in SEVERITIES else \
            max((by_id[x]["risk_severity"] for x in ids), key=lambda s: SEVERITY_RANK[s])
        risks.append({
            "title": title, "severity": severity, "finding_ids": ids, "rules": cited_rules,
            "analysis": str(r.get("analysis", "")).strip()[:1200],
            "why_non_obvious": str(r.get("why_non_obvious", "")).strip()[:400],
            "recommended_action": str(r.get("recommended_action", "")).strip()[:400],
            "needs_human_review": bool(RULE_WORDING.search(text)) or any((by_id[x].get("sentinel") or {}).get("human_review") for x in ids),
            "removed_ids": removed, "absence_claim": bool(ABSENCE.search(text)), "rule_wording": bool(RULE_WORDING.search(text)),
            "evidence": [{"finding_id": x, **_citation(by_id[x]["citations"][0], cik)}
                         for x in ids if by_id[x].get("citations")],
        })
        if len(risks) == MAX_RISKS:
            break
    return risks, dropped


def draft_memo(report: dict, complete: Callable[..., Any]) -> dict:
    findings = eligible_findings(report)
    rules = allowed_rules(report)
    by_id = {f["id"]: f for f in findings}
    h = report.get("health") or {}
    base = {
        "company": report.get("company"), "cik": report.get("cik"), "as_of": report.get("as_of"),
        "decision": report.get("decision", ""),
        "health": {"score": h.get("score"), "band": h.get("band"), "coverage_pct": (h.get("coverage") or {}).get("pct")} if h else None,
        "evidence_gaps": [{"id": f["id"], "title": f["title"]} for f in report.get("findings", [])
                          if f.get("evidence_confidence") == "insufficient"],
        "disclaimer": DISCLAIMER, "risks": [], "dropped": [], "usage": None, "executive_summary": "",
    }
    if len(findings) < 2 or not rules:
        return {**base, "status": "insufficient",
                "status_note": "Insufficient verified findings or rules to support a reliable memo."}

    system = PROMPT.read_text(encoding="utf-8").replace("{company}", str(report.get("company"))) \
        .replace("{decision}", report.get("decision") or "a general governance review")
    messages = [{"role": "system", "content": system},
                {"role": "user", "content": build_pack(report, findings, rules)}]
    try:
        r = complete("reason", messages, json_mode=True, max_tokens=2500, max_wait=75)
    except LLMError as exc:
        return {**base, "status": "unavailable", "status_note": f"Memo model unavailable: {exc}"[:300]}

    risks, dropped = validate_risks(r.data, by_id, rules, str(report.get("cik", "")))
    data = r.data if isinstance(r.data, dict) else {}
    status = "complete" if len(risks) >= MIN_RISKS else "insufficient"
    note = "" if status == "complete" else f"Only {len(risks)} risk(s) passed citation checks (minimum {MIN_RISKS})."
    usage = {"node": "memo", "provider": r.provider, "model": r.model, "input_tokens": r.input_tokens,
             "output_tokens": r.output_tokens, "latency_ms": r.latency_ms, "cached": r.cached}
    return {**base, "status": status, "status_note": note, "generated_by": r.model,
            "executive_summary": str(data.get("executive_summary", "")).strip()[:900],
            "risks": risks, "dropped": dropped, "usage": usage}


def to_markdown(memo: dict) -> str:
    out = [f"# Legal Risk Memo: {memo.get('company')}", "",
           f"**Analysis date (evidence frozen):** {memo.get('as_of')}  ",
           f"**Decision:** {memo.get('decision') or 'General governance review'}  ",
           f"**Status:** {memo.get('status')}" + (f" ({memo['status_note']})" if memo.get("status_note") else "")]
    if memo.get("health"):
        h = memo["health"]
        out.append(f"**Governance Health Score:** {h['score']}/100 ({h['band']}), evidence coverage {h['coverage_pct']}%")
    out += ["", "## Executive summary", memo.get("executive_summary") or "-", "", "## Non-obvious risks"]
    for i, r in enumerate(memo.get("risks", []), 1):
        out += ["", f"### {i}. {r['title']} ({r['severity']})"
                + (" - depends on human review" if r["needs_human_review"] else ""),
                r["analysis"] + (" *(Absence statements mean: not found in the reviewed passages.)*" if r.get("absence_claim") else "") + (" *(Rule wording needs legal review: Reg S-K items are disclosure requirements.)*" if r.get("rule_wording") else ""), "", f"*Why non-obvious:* {r['why_non_obvious']}", "",
                f"*Rules:* {', '.join(r['rules'])}  ", f"*Recommended action:* {r['recommended_action']}", "",
                "*Evidence:*"]
        for e in r["evidence"]:
            out.append(f"- [{e['finding_id']}] {e.get('form') or ''} p.{e.get('page')}: \"{(e.get('quote') or '')[:160]}\" ({e.get('source_url')})")
    if memo.get("evidence_gaps"):
        out += ["", "## Evidence gaps (could not be confirmed from public filings)"]
        out += [f"- [{g['id']}] {g['title']}" for g in memo["evidence_gaps"]]
    out += ["", "---", f"*{memo['disclaimer']}*"]
    return "\n".join(out)


def _main(argv: list[str]) -> int:
    from app.llm.client import get_llm

    if len(argv) != 2:
        print("usage: python -m app.agents.memo <saved report .json>")
        return 1
    path = Path(argv[1])
    report = json.loads(path.read_text(encoding="utf-8"))
    if "health" not in report:
        from app.agents.score import health_score
        report = {**report, "health": health_score(report)}
    memo = draft_memo(report, get_llm().complete)
    md = to_markdown(memo)
    print(md)
    print(f"\nstatus={memo['status']} risks={len(memo['risks'])} dropped={len(memo['dropped'])}")
    for d in memo["dropped"]:
        print(f"  dropped: {d}")
    for r in memo["risks"]:
        if r["removed_ids"]:
            print(f"  removed unknown ids from '{r['title']}': {r['removed_ids']}")
    if memo.get("usage"):
        u = memo["usage"]
        print(f"usage: {u['model']} in={u['input_tokens']} out={u['output_tokens']} {u['latency_ms']} ms cached={u['cached']}")
    stem = path.stem.replace("_sentinel", "")
    (path.parent / f"{stem}_memo.json").write_text(json.dumps(memo, indent=1, default=str), encoding="utf-8")
    (path.parent / f"{stem}_memo.md").write_text(md, encoding="utf-8")
    print(f"saved: {path.parent / (stem + '_memo.md')}")
    return 0


if __name__ == "__main__":
    sys.exit(_main(sys.argv))