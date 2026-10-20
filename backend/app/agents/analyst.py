"""Decision-question analyst (LLM): answers each decision question strictly from an evidence pack.

Evidence pack: E# = retrieved passages (per question), G# = verified graph facts, R# = rule results.
The model must cite evidence ids. Citations that are not in the pack are dropped, and an answer left
without a valid citation is downgraded to "insufficient". Severity comes from the model (how serious
if confirmed); evidence confidence is set by code (answered = medium, partial = low) until the
Reliability Sentinel reviews it.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from app.ingest.forms import form_of
from app.agents.findings import Finding
from app.rules.engine import Citation

PROMPT_PATH = Path(__file__).resolve().parent.parent / "prompts" / "analyze_questions.v2.md"
PASSAGE_CHARS = 700
COMPACT_PASSAGE_CHARS = 350
MAX_GRAPH_ITEMS = 12
SECTION_FOR = {"relationship": "conflict_review", "consistency": "disclosure_verification",
               "regulatory": "regulatory_check", "missing_evidence": "disclosure_verification"}
SEVERITIES = {"low", "medium", "high", "critical"}
STATUSES = {"answered", "partial", "insufficient"}
INSUFFICIENT_TEXT = "Insufficient evidence to reach a reliable conclusion."


def system_prompt(company: str) -> str:
    return PROMPT_PATH.read_text(encoding="utf-8").replace("{company}", company)


def _graph_priority(row: dict, officers: set[str]) -> int:
    if row["kind"] == "BOARD_SEAT" and row["person_key"] in officers:
        return 0
    return {"RELATED_TRANSACTION": 1, "OFFICER_OF": 2, "CHAIRS_BOARD": 3, "MEMBER_OF": 4}.get(row["kind"], 9)


def build_pack(answers: list[dict], facts: Any, rule_report: dict, compact: bool = False) -> tuple[str, dict[str, Citation]]:
    """Text evidence pack for the model, plus an index from evidence id to citation."""
    lines: list[str] = []
    index: dict[str, Citation] = {}
    chars, per_question = (COMPACT_PASSAGE_CHARS, 1) if compact else (PASSAGE_CHARS, 3)

    n = 0
    for qi, a in enumerate(answers, start=1):
        lines.append(f"\n## Q{qi} [{a['investigation']}] {a['question']}")
        for h in a.get("hits", [])[:per_question]:
            n += 1
            eid = f"E{n}"
            text = " ".join(h["text"].split())[:chars]
            lines.append(f"{eid} ({h['form']} filed {h['filing_date']}, {h['section_title']}, p.{h['page_start']}): {text}")
            index[eid] = Citation(accession_no=h["accession_no"], form=h["form"], filing_date=h["filing_date"],
                                  section=h["section_title"], page=h["page_start"], chunk_id=h["chunk_id"], quote=text)

    officers = {r["person_key"] for r in facts.relations if r["kind"] == "OFFICER_OF"}
    useful = [r for r in facts.relations
              if r["kind"] in ("OFFICER_OF", "BOARD_SEAT", "RELATED_TRANSACTION", "CHAIRS_BOARD")
              or (r["kind"] == "MEMBER_OF" and r["chair"])]
    useful.sort(key=lambda r: _graph_priority(r, officers))
    if useful:
        lines.append("\n## Verified governance graph facts")
        for i, r in enumerate(useful[:MAX_GRAPH_ITEMS], start=1):
            gid = f"G{i}"
            quote = r["props"].get("quote") or ""
            lines.append(f"{gid}: {r['person_name']} {r['kind']} {r['org_name']} (p.{r['props'].get('page')}): \"{quote[:200]}\"")
            index[gid] = Citation(accession_no=r["props"]["accession_no"], form=form_of(r["props"]["accession_no"]), section=r["props"].get("section"),
                                  page=r["props"].get("page"), chunk_id=r["props"].get("chunk_id"), quote=quote)

    results = rule_report.get("results", [])
    if results:
        lines.append("\n## Governance Rule Engine results")
        for i, r in enumerate(results, start=1):
            rid = f"R{i}"
            lines.append(f"{rid}: {r['source']} - {r['title']} = {r['result']} ({r['rationale'][:160]})")
            if r.get("evidence"):
                index[rid] = Citation(**r["evidence"][0])
    return "\n".join(lines), index


def parse_analysis(data: Any, answers: list[dict], index: dict[str, Citation]) -> list[dict]:
    """Validate the model output; every question gets an entry (missing ones become insufficient)."""
    items = data.get("answers", []) if isinstance(data, dict) else []
    by_question: dict[int, dict] = {}
    for item in items:
        try:
            qi = int(item.get("question")) - 1
        except (TypeError, ValueError):
            continue
        if 0 <= qi < len(answers):
            by_question[qi] = item

    analysis = []
    for qi, a in enumerate(answers):
        item = by_question.get(qi, {})
        status = item.get("status") if item.get("status") in STATUSES else "insufficient"
        cites = [c for c in item.get("citations", []) or [] if isinstance(c, str) and c in index]
        if status != "insufficient" and not cites:
            status = "insufficient"
        severity = item.get("risk_severity") if item.get("risk_severity") in SEVERITIES else "low"
        answer = str(item.get("answer") or "")[:800] if status != "insufficient" else INSUFFICIENT_TEXT
        analysis.append({"question": a["question"], "investigation": a["investigation"], "status": status,
                         "answer": answer, "citations": cites if status != "insufficient" else [],
                         "risk_severity": severity, "recommended_action": str(item.get("recommended_action") or "")[:300]})
    return analysis


def analysis_findings(analysis: list[dict], index: dict[str, Citation]) -> list[Finding]:
    out: list[Finding] = []
    for a in analysis:
        if a["status"] == "insufficient":
            continue
        out.append(Finding(
            investigation=a["investigation"], report_section=SECTION_FOR[a["investigation"]],
            title=f"Decision question: {a['question'][:140]}", claim=a["answer"],
            risk_severity=a["risk_severity"],
            # absence claims and partial answers stay low until the Reliability Sentinel reviews them
            evidence_confidence="medium" if a["status"] == "answered" and a["investigation"] != "missing_evidence" else "low",
            citations=[index[c] for c in a["citations"]],
            recommended_actions=[a["recommended_action"]] if a["recommended_action"] else [],
            decision_question=a["question"], source="llm",
        ))
    return out


def missing_inputs(analysis: list[dict], answers: list[dict]) -> list[dict]:
    """Questions for Missing Evidence Detection: the analyst's verdict wins when available."""
    if not analysis:
        return answers
    return [{"question": a["question"], "investigation": a["investigation"], "hits": []}
            for a in analysis if a["status"] == "insufficient"]