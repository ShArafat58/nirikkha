"""LangGraph orchestration of a Governance Crash-Test.

    redact -> guard -> collect -> plan -> gather -> analyze -> [relationship | consistency | regulatory | missing_evidence]
          -> merge -> sentinel -> score

- guard:    heuristic checks, then the safety model (gpt-oss-safeguard) classifies the decision text.
- collect:  facts + Governance Rule Engine results (evidence frozen at as_of).
- plan:     decision-specific stress test: the decision becomes up to 8 questions across the 4 investigations.
- gather:   retrieval for each question (filed on or before as_of only).
- analyze:  the analyst model answers each question ONLY from an evidence pack (passages, graph facts, rules),
            citing evidence ids; answers without valid citations become "insufficient".
- the 4 deterministic investigations run in parallel; merge numbers and ranks findings and adds usage.
- sentinel: AI Reliability Sentinel checks every finding (source, period, sufficiency, contradiction, judge-model
            support, human review). Severity never changes; confidence can only go down.
Every node appends a timed event (used for live progress in the UI).

Run directly:
    python -m app.agents.graph 719739 --as-of 2023-03-10 --decision "Before we proceed with a deposit partnership with this bank, identify the governance risks and evidence gaps we should investigate."
"""

from __future__ import annotations

import argparse
import hashlib
import json
import operator
import re
import sys
import time
from collections import Counter
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path
from typing import Annotated, Any, Callable, TypedDict

from langgraph.graph import END, START, StateGraph

from app.agents.analyst import analysis_findings, build_pack, missing_inputs, parse_analysis, system_prompt
from app.agents.findings import (
    Finding, consistency_findings, missing_evidence_findings, number_findings, regulatory_findings,
    relationship_findings,
)
from app.agents.report import build_sections
from app.agents.score import health_score
from app.agents.sentinel import review_findings
from app.guardrails.pii import redact_pii
from app.llm.client import LLMError
from app.rules.engine import evaluate

PROMPTS = Path(__file__).resolve().parent.parent / "prompts"
PLAN_PROMPT = "plan_decision.v2.md"
INVESTIGATIONS = ("relationship", "consistency", "regulatory", "missing_evidence")
MAX_DECISION_CHARS = 1500
MAX_QUESTIONS = 8
INJECTION = re.compile(
    r"ignore (all |any )?(previous|prior|above) instructions|system prompt|you are now|jailbreak|developer mode", re.I
)
SEVERITY_ORDER = {"critical": 0, "high": 1, "medium": 2, "low": 3}
DEFAULT_QUESTIONS = [
    {"investigation": "relationship", "question": "Do any directors or executive officers have outside roles that could create potential conflicts of interest?"},
    {"investigation": "consistency", "question": "Did the company's risk disclosures change materially compared with the previous year?"},
    {"investigation": "regulatory", "question": "Do the governance disclosures cover Regulation S-K Items 401, 402, 404 and 407?"},
    {"investigation": "missing_evidence", "question": "Which governance facts needed for this decision cannot be confirmed from public filings?"},
]


class CrashTestState(TypedDict, total=False):
    cik: str
    as_of: str
    decision: str
    allowed: bool
    guard_result: dict
    pii: dict
    questions: list[dict]
    facts: Any
    rule_report: dict
    answers: list[dict]
    analysis: list[dict]
    findings: Annotated[list[dict], operator.add]
    events: Annotated[list[dict], operator.add]
    usage: Annotated[list[dict], operator.add]
    report: dict


@dataclass
class Services:
    complete: Callable[..., Any]
    collect_facts: Callable[[str, date], Any]
    retrieve: Callable[..., Any]


def default_services() -> Services:
    from app.llm.client import get_llm
    from app.rag.retrieve import retrieve
    from app.rules.run import collect_facts

    return Services(complete=get_llm().complete, collect_facts=collect_facts, retrieve=retrieve)


def _prompt(name: str, **values: str) -> str:
    text = (PROMPTS / name).read_text(encoding="utf-8")
    for key, value in values.items():
        text = text.replace("{" + key + "}", value)
    return text


def _event(node: str, message: str, started: float, **data) -> dict:
    return {"node": node, "message": message, "ms": int((time.perf_counter() - started) * 1000), **data}


def _usage(node: str, r: Any) -> dict:
    return {"node": node, "provider": r.provider, "model": r.model, "input_tokens": r.input_tokens,
            "output_tokens": r.output_tokens, "latency_ms": r.latency_ms, "cached": r.cached}


def build_graph(services: Services):
    def redact(state: CrashTestState) -> dict:
        started = time.perf_counter()
        decision, pii = redact_pii((state.get("decision") or "").strip())
        message = ("No personal data found" if not pii
                   else "Redacted " + ", ".join(f"{n} {k.lower()}" for k, n in sorted(pii.items())))
        return {"decision": decision, "pii": pii, "events": [_event("redact", message, started)]}

    def guard(state: CrashTestState) -> dict:
        started = time.perf_counter()
        decision = (state.get("decision") or "").strip()
        if len(decision) > MAX_DECISION_CHARS:
            result = {"category": "too_long", "reason": f"Decision text longer than {MAX_DECISION_CHARS} characters."}
            return {"allowed": False, "guard_result": result, "events": [_event("guard", "Blocked: too long", started)]}
        if INJECTION.search(decision):
            result = {"category": "prompt_injection", "reason": "Instruction-override pattern detected."}
            return {"allowed": False, "guard_result": result, "events": [_event("guard", "Blocked: prompt_injection", started)]}
        if not decision:
            result = {"category": "ok", "reason": "No decision text; general crash-test."}
            return {"allowed": True, "guard_result": result, "events": [_event("guard", "Allowed (no decision text)", started)]}
        try:
            r = services.complete("safety", [{"role": "system", "content": _prompt("guard_input.v1.md")},
                                             {"role": "user", "content": decision}], json_mode=True, max_tokens=300)
        except LLMError:
            result = {"category": "ok", "reason": "Safety model unavailable; heuristic checks passed."}
            return {"allowed": True, "guard_result": result,
                    "events": [_event("guard", "Allowed (heuristic only; safety model unavailable)", started)]}
        data = r.data if isinstance(r.data, dict) else {}
        allowed = bool(data.get("allowed", True))
        result = {"category": str(data.get("category", "ok")), "reason": str(data.get("reason", ""))}
        message = "Allowed" if allowed else f"Blocked: {result['category']}"
        return {"allowed": allowed, "guard_result": result, "usage": [_usage("guard", r)],
                "events": [_event("guard", message, started, model=r.model)]}

    def collect(state: CrashTestState) -> dict:
        started = time.perf_counter()
        facts = services.collect_facts(state["cik"], date.fromisoformat(state["as_of"]))
        report = evaluate(facts)
        message = (f"{len(facts.filings)} filings, {len(facts.relations)} graph facts, "
                   f"{len(report['results'])} rules evaluated ({report['summary']['by_result']})")
        return {"facts": facts, "rule_report": report, "events": [_event("collect", message, started)]}

    def plan(state: CrashTestState) -> dict:
        started = time.perf_counter()
        decision = (state.get("decision") or "").strip()
        if not decision:
            return {"questions": DEFAULT_QUESTIONS, "events": [_event("plan", "Default questions (no decision)", started)]}
        company = state["facts"].company
        try:
            r = services.complete("fast", [{"role": "system", "content": _prompt(PLAN_PROMPT, company=company)},
                                           {"role": "user", "content": f"Company: {company}\nDecision: {decision}"}],
                                  json_mode=True, max_tokens=700)
            raw = (r.data or {}).get("questions", []) if isinstance(r.data, dict) else []
            questions = [{"investigation": q["investigation"], "question": q["question"].strip()[:300]}
                         for q in raw if isinstance(q, dict) and q.get("investigation") in INVESTIGATIONS
                         and isinstance(q.get("question"), str) and q["question"].strip()][:MAX_QUESTIONS]
            if not questions:
                raise ValueError("planner returned no valid questions")
        except (LLMError, ValueError):
            return {"questions": DEFAULT_QUESTIONS, "events": [_event("plan", "Planner unavailable; default questions", started)]}
        return {"questions": questions, "usage": [_usage("plan", r)],
                "events": [_event("plan", f"{len(questions)} decision-specific questions", started, model=r.model)]}

    def gather(state: CrashTestState) -> dict:
        started = time.perf_counter()
        facts = state["facts"]
        before = facts.as_of + timedelta(days=1)
        answers = []
        for q in state["questions"]:
            hits, _ = services.retrieve(q["question"], k=3, cik=facts.cik, before=before)
            answers.append({**q, "hits": [h.model_dump(mode="json") for h in hits]})
        return {"answers": answers, "events": [_event("gather", f"Evidence retrieved for {len(answers)} questions", started)]}

    def analyze(state: CrashTestState) -> dict:
        started = time.perf_counter()
        facts, answers = state["facts"], state.get("answers", [])
        if not answers:
            return {"analysis": [], "events": [_event("analyze", "No questions to analyze", started)]}
        decision = (state.get("decision") or "").strip() or "(general crash-test)"
        for compact, task in ((False, "analyze"), (True, "reason")):
            pack, index = build_pack(answers, facts, state["rule_report"], compact=compact)
            messages = [{"role": "system", "content": system_prompt(facts.company)},
                        {"role": "user", "content": f"Decision: {decision}\nAnalysis date: {facts.as_of}\n{pack}"}]
            try:
                r = services.complete(task, messages, json_mode=True, max_tokens=1500 if compact else 2000, max_wait=75)
            except LLMError:
                continue
            analysis = parse_analysis(r.data, answers, index)
            found = analysis_findings(analysis, index)
            counts = Counter(a["status"] for a in analysis)
            message = (f"{counts.get('answered', 0)} answered, {counts.get('partial', 0)} partial, "
                       f"{counts.get('insufficient', 0)} insufficient{' (compact pack)' if compact else ''}")
            return {"analysis": analysis, "findings": [f.model_dump(mode="json") for f in found],
                    "usage": [_usage("analyze", r)], "events": [_event("analyze", message, started, model=r.model)]}
        return {"analysis": [], "events": [_event("analyze", "Analyst unavailable; deterministic findings only", started)]}

    def _investigation(name: str, produce: Callable[[CrashTestState], list[Finding]]):
        def node(state: CrashTestState) -> dict:
            started = time.perf_counter()
            found = produce(state)
            return {"findings": [f.model_dump(mode="json") for f in found],
                    "events": [_event(name, f"{len(found)} findings", started)]}
        return node

    def merge(state: CrashTestState) -> dict:
        started = time.perf_counter()
        findings = number_findings([Finding(**f) for f in state.get("findings", [])])
        findings.sort(key=lambda f: (SEVERITY_ORDER[f.risk_severity], f.id))
        facts, usage = state["facts"], state.get("usage", [])
        report = {
            "company": facts.company, "cik": facts.cik, "as_of": facts.as_of.isoformat(),
            "decision": state.get("decision", ""), "pii_redacted": state.get("pii", {}), "guard": state.get("guard_result"),
            "questions": state.get("questions", []), "analysis": state.get("analysis", []),
            "findings": [f.model_dump(mode="json") for f in findings],
            "rule_report": state["rule_report"],
            "summary": {
                "findings": len(findings),
                "by_severity": dict(Counter(f.risk_severity for f in findings)),
                "by_confidence": dict(Counter(f.evidence_confidence for f in findings)),
                "by_investigation": dict(Counter(f.investigation for f in findings)),
                "by_source": dict(Counter(f.source for f in findings)),
            },
            "usage": {
                "llm_calls": len(usage),
                "input_tokens": sum(u["input_tokens"] for u in usage),
                "output_tokens": sum(u["output_tokens"] for u in usage),
                "cost_usd": 0.0,
                "calls": usage,
            },
        }
        return {"report": report, "events": [_event("merge", f"{len(findings)} findings ranked by severity", started)]}

    def sentinel(state: CrashTestState) -> dict:
        started = time.perf_counter()
        report, usages = review_findings(state["report"], state["facts"], services.complete)
        s = report["summary"]["sentinel"]
        message = (f"{s['verified']} verified, {s['needs_review']} need review, {s['downgraded']} downgraded, "
                   f"{s['unsupported']} unsupported; {s['human_review']} for human review")
        return {"report": report, "usage": usages, "events": [_event("sentinel", message, started)]}

    def score(state: CrashTestState) -> dict:
        started = time.perf_counter()
        health = health_score(state["report"])
        message = (f"Health {health['score']}/100 ({health['band']}), coverage {health['coverage']['pct']}%, "
                   f"{health['insufficient_evidence']['count']} insufficient")
        return {"report": {**state["report"], "health": health, "sections": build_sections(state["report"])}, "events": [_event("score", message, started)]}

    graph = StateGraph(CrashTestState)
    graph.add_node("guard", guard)
    graph.add_node("collect", collect)
    graph.add_node("plan", plan)
    graph.add_node("gather", gather)
    graph.add_node("analyze", analyze)
    graph.add_node("relationship", _investigation("relationship", lambda s: relationship_findings(s["facts"])))
    graph.add_node("consistency", _investigation("consistency", lambda s: consistency_findings(s["facts"])))
    graph.add_node("regulatory", _investigation("regulatory", lambda s: regulatory_findings(s["rule_report"])))
    graph.add_node("missing_evidence", _investigation(
        "missing_evidence",
        lambda s: missing_evidence_findings(s["rule_report"], s["facts"],
                                            missing_inputs(s.get("analysis", []), s.get("answers", [])))))
    graph.add_node("merge", merge)
    graph.add_node("sentinel", sentinel)

    graph.add_node("redact", redact)
    graph.add_edge(START, "redact")
    graph.add_edge("redact", "guard")
    graph.add_conditional_edges("guard", lambda s: "collect" if s.get("allowed") else "end",
                                {"collect": "collect", "end": END})
    graph.add_edge("collect", "plan")
    graph.add_edge("plan", "gather")
    graph.add_edge("gather", "analyze")
    for name in INVESTIGATIONS:
        graph.add_edge("analyze", name)
    graph.add_edge(list(INVESTIGATIONS), "merge")
    graph.add_edge("merge", "sentinel")
    graph.add_node("score", score)
    graph.add_edge("sentinel", "score")
    graph.add_edge("score", END)
    return graph.compile()


def run_crash_test(cik: str, decision: str = "", as_of: date | None = None, services: Services | None = None) -> dict:
    app = build_graph(services or default_services())
    initial: CrashTestState = {"cik": cik, "as_of": (as_of or date.today()).isoformat(), "decision": decision,
                               "findings": [], "events": [], "usage": []}
    return app.invoke(initial)


def _main(argv: list[str]) -> int:
    from app.config import get_settings
    from app.db import DatabaseError

    parser = argparse.ArgumentParser(description="Run a Governance Crash-Test")
    parser.add_argument("cik")
    parser.add_argument("--as-of", type=date.fromisoformat)
    parser.add_argument("--decision", default="")
    args = parser.parse_args(argv[1:])

    try:
        state = run_crash_test(args.cik, args.decision, args.as_of)
    except (DatabaseError, ValueError) as exc:
        print(f"ERROR: {exc}")
        return 1

    print("== progress ==")
    for e in state["events"]:
        print(f"  {e['node']:17} {e['ms']:>6} ms  {e['message']}")
    if not state.get("allowed"):
        print(f"\nBLOCKED by guard: {state.get('guard_result')}")
        return 2

    report = state["report"]
    print("\n== decision questions -> analyst ==")
    for a in report["analysis"] or [{"question": q["question"], "status": "-", "investigation": q["investigation"]}
                                    for q in report["questions"]]:
        print(f"  [{a['investigation']}] ({a['status']}) {a['question']}")
    print(f"\n== findings ({report['summary']}) ==")
    for f in report["findings"]:
        s = f.get("sentinel") or {}
        flag = " HUMAN REVIEW" if s.get("human_review") else ""
        print(f"\n  {f['id']:6} severity={f['risk_severity']:8} confidence={f['evidence_confidence']:12} "
              f"{f['source']:13} sentinel={s.get('verdict', '-')}{flag}")
        print(f"         {f['title']}")
        print(f"         {f['claim'][:240]}")
        if f["citations"]:
            c = f["citations"][0]
            print(f"         evidence: {c.get('form') or ''} {c['accession_no']} p.{c.get('page')} \"{' '.join(c['quote'].split())[:120]}\"")
        if f["recommended_actions"]:
            print(f"         action: {f['recommended_actions'][0]}")
    h = report.get("health")
    if h:
        print(f"\nGovernance Health Score {h['score']}/100 ({h['band']}), coverage {h['coverage']['pct']}% "
              f"({h['coverage']['label']}), insufficient {h['insufficient_evidence']['count']}, human review {h['human_review']}")
        for w in h["warnings"]:
            print(f"  WARNING: {w}")
    u = report["usage"]
    print(f"\nLLM calls={u['llm_calls']} tokens in={u['input_tokens']} out={u['output_tokens']} cost=${u['cost_usd']}")

    digest = hashlib.sha256(args.decision.encode("utf-8")).hexdigest()[:8]
    out_dir = get_settings().cache_dir / "analyses"
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / f"{report['cik']}_{report['as_of']}_{digest}.json"
    out.write_text(json.dumps({**report, "events": state["events"]}, indent=1, default=str), encoding="utf-8")
    print(f"saved: {out}")
    return 0


if __name__ == "__main__":
    sys.exit(_main(sys.argv))