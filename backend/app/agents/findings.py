"""Deterministic investigation steps (no LLM): turn facts and rule results into evidence-linked findings.

Findings follow docs/SPEC.md: risk_severity and evidence_confidence are separate fields; a disclosed
relationship is a question to review, never an accusation; missing information is reported as
"insufficient evidence", never as low risk.
"""

from __future__ import annotations

import re
from typing import Literal

from pydantic import BaseModel

from app.rules.engine import (
    RELATED_PERSON_THRESHOLD_USD, RISK_SECTIONS, YOY_FLAG_PCT, YOY_MIN_CHARS, Citation, Facts, parse_amount,
)

Investigation = Literal["relationship", "consistency", "regulatory", "missing_evidence"]
ReportSection = Literal["disclosure_verification", "conflict_review", "regulatory_check", "recommended_action"]
Severity = Literal["low", "medium", "high", "critical"]
EvidenceConfidence = Literal["high", "medium", "low", "insufficient"]

SENSITIVE_ORG = re.compile(
    r"federal reserve|reserve bank|\bfdic\b|comptroller|securities and exchange|regulator|treasury|\bbank\b", re.I
)
STALE_FACTS_DAYS = 180       # proxy facts older than this at the analysis date may have changed
WEAK_EVIDENCE_SCORE = 0.0    # cross-encoder score below this: the passage does not answer the question

RULE_ACTIONS: dict[str, list[str]] = {
    "R407_FIN_EXPERT": ["Confirm whether the audit committee has a designated financial expert (latest proxy, 10-K Item 10)."],
    "R402_SCT": ["Locate the Summary Compensation Table; check whether it appears under a different heading."],
    "R402_PVP": ["Locate the Pay versus Performance disclosure required for this fiscal year."],
    "R404_POLICY": ["Request the written related-person transaction policy."],
    "BP_CRO": ["Confirm who currently holds the Chief Risk Officer role and since when."],
    "BP_RISK_COMMITTEE": ["Confirm which board committee oversees enterprise risk."],
}


class Finding(BaseModel):
    id: str = ""
    investigation: Investigation
    report_section: ReportSection
    title: str
    claim: str
    risk_severity: Severity
    evidence_confidence: EvidenceConfidence
    citations: list[Citation] = []
    recommended_actions: list[str] = []
    rule_id: str | None = None
    decision_question: str | None = None
    source: Literal["deterministic", "llm"] = "deterministic"


def _cite(row: dict) -> Citation:
    pr = row["props"]
    return Citation(accession_no=pr["accession_no"], form="DEF 14A", section=pr.get("section"), page=pr.get("page"),
                    chunk_id=pr.get("chunk_id"), quote=pr.get("quote") or "")


def _row_confidence(rows: list[dict]) -> EvidenceConfidence:
    return "medium" if any(r["props"].get("from_table") for r in rows) else "high"


# ---------- Relationship Investigation ----------

def relationship_findings(facts: Facts) -> list[Finding]:
    out: list[Finding] = []
    officers = {r["person_key"]: r for r in facts.rows("OFFICER_OF")}

    seats_by_officer: dict[str, list[dict]] = {}
    for r in facts.rows("BOARD_SEAT"):
        if r["person_key"] in officers:
            seats_by_officer.setdefault(r["person_key"], []).append(r)
    for key, seats in seats_by_officer.items():
        name = seats[0]["person_name"]
        title = officers[key]["props"].get("title") or "executive officer"
        orgs = ", ".join(s["org_name"] for s in seats)
        sensitive = any(SENSITIVE_ORG.search(s["org_name"]) for s in seats)
        out.append(Finding(
            investigation="relationship", report_section="conflict_review",
            title=f"{name} ({title}) holds outside board seats",
            claim=(f"Filings disclose that {name} serves on the boards of: {orgs}. This may raise conflict-of-interest "
                   f"questions for decisions involving these organizations; a disclosed relationship is not evidence of misconduct."),
            risk_severity="high" if sensitive else "low",
            evidence_confidence=_row_confidence(seats),
            citations=[_cite(s) for s in seats],
            recommended_actions=[
                "Confirm each outside role is still current (latest proxy, Form 8-K Item 5.02).",
                "Check whether any of these organizations is a party to, or regulator of, the decision under review.",
                "Review the company's conflict-of-interest and recusal policies for these roles.",
            ],
        ))

    insiders = {r["person_key"] for r in facts.rows("OFFICER_OF") + facts.rows("DIRECTOR_OF")}
    by_org: dict[str, list[dict]] = {}
    for r in facts.rows("BOARD_SEAT") + facts.rows("EMPLOYED_BY"):
        if r["person_key"] in insiders:
            by_org.setdefault(r["org_key"], []).append(r)
    for rows in by_org.values():
        people = {r["person_key"]: r for r in rows}
        if len(people) >= 2:
            org = rows[0]["org_name"]
            names = ", ".join(sorted(r["person_name"] for r in people.values()))
            out.append(Finding(
                investigation="relationship", report_section="conflict_review",
                title=f"Shared outside affiliation: {org}",
                claim=f"{names} are disclosed as having served at {org}. Shared affiliations are common and are not a conflict by themselves.",
                risk_severity="low", evidence_confidence=_row_confidence(rows),
                citations=[_cite(r) for r in people.values()],
                recommended_actions=[f"Review only if {org} is a counterparty or competitor in the decision."],
            ))

    for r in facts.rows("RELATED_TRANSACTION"):
        amount = parse_amount(r["props"].get("amount"))
        if amount is not None and amount >= RELATED_PERSON_THRESHOLD_USD:
            out.append(Finding(
                investigation="relationship", report_section="disclosure_verification",
                title=f"Related-party transaction disclosed: {r['person_name']}",
                claim=(f"The proxy discloses a related-party item with {r['person_name']} of {r['props'].get('amount')}, "
                       f"above the ${RELATED_PERSON_THRESHOLD_USD:,} threshold of Reg S-K Item 404(a)."),
                risk_severity="medium", evidence_confidence=_row_confidence([r]), citations=[_cite(r)],
                recommended_actions=[
                    "Verify approval under the related-person transaction policy (Item 404(b)).",
                    f"Check whether {r['person_name']} is involved in the decision under review.",
                ],
            ))
    return out


# ---------- Cross-Document Consistency Check ----------

def consistency_findings(facts: Facts) -> list[Finding]:
    out: list[Finding] = []
    tenks = sorted((f for f in facts.filings if f["form"] == "10-K" and f["filing_date"] <= facts.as_of),
                   key=lambda f: f["filing_date"])
    if len(tenks) >= 2:
        prev, cur = tenks[-2], tenks[-1]
        for r in facts.yoy:
            pct, prev_chars = r.get("change_pct"), r.get("prev_chars")
            if (pct is None or not prev_chars or r["section_key"] not in RISK_SECTIONS or abs(pct) < YOY_FLAG_PCT
                    or max(r["chars"], prev_chars) < YOY_MIN_CHARS):
                continue
            shrank = pct < 0
            out.append(Finding(
                investigation="consistency", report_section="disclosure_verification",
                title=f"{r['title']} {'shrank' if shrank else 'grew'} {abs(pct):.1f}% year over year",
                claim=(f"The section {'shrank' if shrank else 'grew'} from {prev_chars:,} characters in the 10-K filed "
                       f"{prev['filing_date']} to {r['chars']:,} characters in the 10-K filed {cur['filing_date']}. "
                       f"Size alone does not show what changed; the content must be compared."),
                risk_severity="high" if shrank and r["section_key"] in {"item_1a", "item_7a"} else "medium",
                evidence_confidence="medium",
                citations=[
                    Citation(accession_no=prev["accession_no"], form="10-K", filing_date=prev["filing_date"].isoformat(),
                             section=r["title"], quote=r["title"]),
                    Citation(accession_no=cur["accession_no"], form="10-K", filing_date=cur["filing_date"].isoformat(),
                             section=r["title"], quote=r["title"]),
                ],
                recommended_actions=[
                    "Compare both versions of the section side by side.",
                    "Ask whether content moved to another section or was removed.",
                    "If a risk description was removed, ask why it no longer applies.",
                ],
            ))

    chairs: dict[str, list[dict]] = {}
    for r in facts.rows("MEMBER_OF"):
        if r["chair"]:
            chairs.setdefault(r["org_name"], []).append(r)
    for committee, rows in chairs.items():
        if len({r["person_key"] for r in rows}) > 1:
            names = ", ".join(sorted({r["person_name"] for r in rows}))
            out.append(Finding(
                investigation="consistency", report_section="disclosure_verification",
                title=f"{committee}: more than one chair recorded",
                claim=f"The proxy evidence names more than one chair of the {committee} ({names}). This may be a table reading issue or a mid-year change.",
                risk_severity="low", evidence_confidence="low", citations=[_cite(r) for r in rows],
                recommended_actions=[f"Verify the current chair of the {committee} in the committee section of the proxy."],
            ))
    return out


# ---------- Regulatory Rule Check ----------

def regulatory_findings(rule_report: dict) -> list[Finding]:
    out: list[Finding] = []
    for r in rule_report.get("results", []):
        if r["category"] not in ("law", "best_practice") or r["result"] not in ("POTENTIAL_GAP", "FAIL"):
            continue
        severity: Severity = "high" if r["result"] == "FAIL" else ("medium" if r["category"] == "law" else "low")
        out.append(Finding(
            investigation="regulatory", report_section="regulatory_check",
            title=f"{r['source']}: {r['title']}", claim=r["rationale"],
            risk_severity=severity, evidence_confidence=r["confidence"],
            citations=[Citation(**c) for c in r.get("evidence", [])], rule_id=r["rule_id"],
            recommended_actions=RULE_ACTIONS.get(r["rule_id"], ["Review this requirement with legal or compliance."]),
        ))
    return out


# ---------- Missing Evidence Detection ----------

def missing_evidence_findings(rule_report: dict, facts: Facts, answers: list[dict] | None = None) -> list[Finding]:
    out: list[Finding] = []
    for r in rule_report.get("results", []):
        if r["result"] != "INSUFFICIENT_EVIDENCE":
            continue
        out.append(Finding(
            investigation="missing_evidence", report_section="disclosure_verification",
            title=f"Cannot confirm: {r['title']}",
            claim=f"Insufficient evidence to reach a reliable conclusion. {r['rationale']}",
            risk_severity="medium" if r["category"] == "law" else "low",
            evidence_confidence="insufficient", rule_id=r["rule_id"],
            recommended_actions=["Request the information from the company or check other filings."],
        ))

    proxy = facts.latest("DEF 14A")
    if proxy is not None:
        age = (facts.as_of - proxy["filing_date"]).days
        if age > STALE_FACTS_DAYS:
            out.append(Finding(
                investigation="missing_evidence", report_section="disclosure_verification",
                title="Board and officer facts may have changed since the last proxy",
                claim=(f"Director, committee and officer information comes from the proxy filed {proxy['filing_date']}, "
                       f"{age} days before the analysis date. Changes after that date are not visible in this filing."),
                risk_severity="medium", evidence_confidence="insufficient",
                citations=[Citation(accession_no=proxy["accession_no"], form="DEF 14A",
                                    filing_date=proxy["filing_date"].isoformat(),
                                    quote=f"DEF 14A filed {proxy['filing_date'].isoformat()}")],
                recommended_actions=[
                    f"Check Form 8-K Item 5.02 filings since {proxy['filing_date']} for director or officer departures and appointments.",
                    "Confirm the current holders of key roles (CEO, CFO, Chief Risk Officer) before relying on them.",
                ],
            ))

    for a in answers or []:
        scores = [h["score"] for h in a.get("hits", [])]
        best = max(scores) if scores else None
        if best is None or best < WEAK_EVIDENCE_SCORE:
            out.append(Finding(
                investigation="missing_evidence", report_section="recommended_action",
                title=f"Not answered by public filings: {a['question']}",
                claim=(f"No passage in the filings available on or before {facts.as_of} reliably answers this question"
                       + (f" (best match score {best:.2f})." if best is not None else " (no matching passage).")),
                risk_severity="medium", evidence_confidence="insufficient", decision_question=a["question"],
                recommended_actions=["Ask the company directly or request supporting documents."],
            ))
    return out


def number_findings(findings: list[Finding]) -> list[Finding]:
    prefix = {"relationship": "REL", "consistency": "CON", "regulatory": "REG", "missing_evidence": "MIS"}
    counters: dict[str, int] = {}
    for f in findings:
        counters[f.investigation] = counters.get(f.investigation, 0) + 1
        f.id = f"{prefix[f.investigation]}-{counters[f.investigation]}"
    return findings