"""Governance Rule Engine: structured, testable rules -> PASS / POTENTIAL_GAP / FAIL / INSUFFICIENT_EVIDENCE.

Each rule states its source, its category (law / best_practice / internal_indicator - never mixed),
the requirement, the evidence it needs, and a deterministic test over collected Facts.
No LLM decides a rule result. Rules that do not apply (for example pay-versus-performance before
it was required) are reported as not applicable, with the reason - never as a failure.

Evidence precision: a passage only supports a rule if the rule's pattern matches inside ONE sentence,
and the quoted evidence starts at that sentence, so the quote visibly supports the claim.

Legal note: requirement texts are simplified summaries of Regulation S-K for screening. Results are
review signals for a qualified person, not legal conclusions, and never evidence of misconduct.
"""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass, field
from datetime import date
from typing import Callable, Literal

from pydantic import BaseModel

Result = Literal["PASS", "POTENTIAL_GAP", "FAIL", "INSUFFICIENT_EVIDENCE"]
Category = Literal["law", "best_practice", "internal_indicator"]
Confidence = Literal["high", "medium", "low"]

RELATED_PERSON_THRESHOLD_USD = 120_000          # Reg S-K Item 404(a)
PVP_FIRST_FISCAL_YEAR_END = date(2022, 12, 16)  # Reg S-K Item 402(v) compliance date
STALE_PROXY_DAYS = 455                          # ~15 months: an annual proxy is overdue
YOY_FLAG_PCT = 25.0
YOY_MIN_CHARS = 2000
RISK_SECTIONS = {"item_1a", "item_7", "item_7a", "item_9a"}

# One pattern per evidence key; it must match within a single sentence ([^.] keeps it inside one).
# The same patterns drive the deterministic phrase search in app.rules.run (Postgres ~*).
SENT = r"(?:[^.]|(?:Mr|Ms|Mrs|Dr|Inc|Co|No|Jr|Sr)\.)"  # any char except a sentence-ending period
RULE_PATTERNS: dict[str, str] = {
    "independence": rf"determined that{SENT}{{0,200}}independen|affirmatively determined|independence determination",
    "rpt_policy": rf"(adopted|maintain|have){SENT}{{0,40}}polic(y|ies){SENT}{{0,40}}(approv|review|govern)|polic(y|ies){SENT}{{0,120}}related (person|party)",
    "risk_oversight": rf"(board|committee){SENT}{{0,60}}(oversight of|oversees?|role in){SENT}{{0,40}}risk|risk oversight (role|function|responsibilit|structure)",
    "financial_expert": rf"(qualif|designat|determin|serv){SENT}{{0,160}}audit committee financial expert|audit committee financial experts?{SENT}{{0,40}}(as defined|within the meaning|under)",
    "other_directorships": r"public company (boards|directorships)|other public company",
    "summary_compensation": r"summary compensation table",
    "risk_leadership_change": (r"(chief risk officer|chief financial officer).{0,150}(separation agreement|ceased serving|ceased to serve|stepped down|step down|resign|departure|departed|vacan|transition from|transition out|transitioned)|(separation agreement|ceased serving|ceased to serve|stepped down|resign|departure|departed|vacan|transition from|transition out|transitioned).{0,150}(chief risk officer|chief financial officer)"),
}


class Citation(BaseModel):
    accession_no: str
    form: str | None = None
    filing_date: str | None = None
    section: str | None = None
    page: int | None = None
    chunk_id: str | None = None
    quote: str


class RuleResult(BaseModel):
    rule_id: str
    source: str
    category: Category
    title: str
    requirement: str
    result: Result
    rationale: str
    confidence: Confidence
    human_review: bool
    evidence: list[Citation] = []


class NotApplicable(BaseModel):
    rule_id: str
    source: str
    title: str
    reason: str


@dataclass
class Passage:
    accession_no: str
    form: str
    filing_date: str
    section: str
    page: int | None
    chunk_id: str
    text: str
    score: float = 0.0


@dataclass
class Facts:
    company: str
    cik: str
    as_of: date
    filings: list[dict] = field(default_factory=list)            # {"accession_no", "form", "filing_date": date}
    sections: dict[str, set[str]] = field(default_factory=dict)  # accession_no -> section keys
    relations: list[dict] = field(default_factory=list)          # graph rows (app.graph.resolve.build_rows)
    relations_source: str | None = None                          # accession the relations came from
    passages: dict[str, list[Passage]] = field(default_factory=dict)
    yoy: list[dict] = field(default_factory=list)                # app.analytics.warehouse.section_yoy rows

    def latest_proxy(self) -> dict | None:
        """Newest proxy statement (DEF 14A or PRE 14A) on or before as_of."""
        from app.ingest.edgar import PROXY_FORMS

        found = [f for f in (self.latest(form) for form in PROXY_FORMS) if f]
        return max(found, key=lambda f: f["filing_date"]) if found else None

    def latest(self, form: str) -> dict | None:
        candidates = [f for f in self.filings if f["form"] == form and f["filing_date"] <= self.as_of]
        return max(candidates, key=lambda f: f["filing_date"]) if candidates else None

    def rows(self, kind: str) -> list[dict]:
        return [r for r in self.relations if r["kind"] == kind]


@dataclass
class Rule:
    id: str
    source: str
    category: Category
    title: str
    requirement: str
    evidence_needed: list[str]
    check: Callable[["Rule", Facts], RuleResult | NotApplicable]


# ---------- helpers ----------

_AMOUNT = re.compile(r"\$\s*([\d,]+(?:\.\d+)?)\s*(thousand|million|billion)?", re.I)


def parse_amount(text: str | None) -> float | None:
    match = _AMOUNT.search(text or "")
    if not match:
        return None
    value = float(match.group(1).replace(",", ""))
    return value * {"thousand": 1e3, "million": 1e6, "billion": 1e9}.get((match.group(2) or "").lower(), 1.0)


def sentence_snippet(text: str, pattern: str, max_len: int = 360) -> str | None:
    """Verbatim quote starting at the sentence that contains the first match (None if no match)."""
    match = re.search(pattern, text, re.I)
    if not match:
        return None
    boundary = max(text.rfind(". ", 0, match.start()), text.rfind("\n", 0, match.start()))
    start = boundary + 1 if boundary >= 0 and match.start() - boundary <= 300 else match.start()
    ends = [i for i in (text.find(". ", match.end()), text.find("\n", match.end())) if i != -1]
    end = min(ends) + 1 if ends else len(text)
    end = max(min(end, start + max_len), match.end())
    return text[start:end].strip()


def _find(facts: Facts, key: str) -> Citation | None:
    pattern = RULE_PATTERNS[key]
    for p in facts.passages.get(key, []):
        quote = sentence_snippet(p.text, pattern)
        if quote:
            return Citation(accession_no=p.accession_no, form=p.form, filing_date=p.filing_date, section=p.section,
                            page=p.page, chunk_id=p.chunk_id, quote=quote)
    return None


def _cite_row(row: dict) -> Citation:
    pr = row["props"]
    return Citation(accession_no=pr["accession_no"], section=pr.get("section"), page=pr.get("page"),
                    chunk_id=pr.get("chunk_id"), quote=pr.get("quote") or "")


def _result(rule: Rule, result: Result, rationale: str, confidence: Confidence, review: bool,
            evidence: list[Citation] | None = None) -> RuleResult:
    return RuleResult(rule_id=rule.id, source=rule.source, category=rule.category, title=rule.title,
                      requirement=rule.requirement, result=result, rationale=rationale,
                      confidence=confidence, human_review=review, evidence=evidence or [])


def _no_relations(rule: Rule, facts: Facts) -> RuleResult | None:
    if facts.latest_proxy() is None:
        return _result(rule, "INSUFFICIENT_EVIDENCE", "No proxy statement (DEF 14A) available on or before the analysis date.",
                       "low", True)
    if facts.relations_source is None:
        return _result(rule, "INSUFFICIENT_EVIDENCE",
                       "Relationship extraction has not been run for the latest proxy; cannot test this rule.", "low", True)
    return None


# ---------- rule checks ----------

def check_directors(rule: Rule, facts: Facts):
    if (missing := _no_relations(rule, facts)) is not None:
        return missing
    directors = facts.rows("DIRECTOR_OF")
    names = sorted({r["person_name"] for r in directors})
    if len(names) >= 3:
        return _result(rule, "PASS", f"{len(names)} directors identified with verified quotes.", "high", False,
                       [_cite_row(r) for r in directors[:3]])
    if names:
        return _result(rule, "POTENTIAL_GAP", f"Only {len(names)} director(s) identified; board list may be incomplete.",
                       "medium", True, [_cite_row(r) for r in directors])
    return _result(rule, "INSUFFICIENT_EVIDENCE", "No verified director identification found.", "low", True)


def check_other_boards(rule: Rule, facts: Facts):
    seats = facts.rows("BOARD_SEAT")
    if seats:  # verified quotes from director biographies are the strongest evidence
        return _result(rule, "PASS", f"{len(seats)} outside board seats disclosed in director biographies.", "high",
                       False, [_cite_row(r) for r in seats[:3]])
    cite = _find(facts, "other_directorships")
    if cite:
        return _result(rule, "PASS", "Other public company directorships are disclosed.", "medium", False, [cite])
    return _result(rule, "INSUFFICIENT_EVIDENCE", "No disclosure of other directorships found.", "low", True)

def check_sct(rule: Rule, facts: Facts):
    proxy = facts.latest_proxy()
    if proxy is None:
        return _result(rule, "INSUFFICIENT_EVIDENCE", "No proxy statement available.", "low", True)
    if "summary_compensation_table" in facts.sections.get(proxy["accession_no"], set()):
        cite = _find(facts, "summary_compensation")
        evidence = [cite] if cite else [Citation(accession_no=proxy["accession_no"], form=proxy["form"],
                                                 filing_date=proxy["filing_date"].isoformat(),
                                                 section="Summary Compensation Table", quote="Summary Compensation Table")]
        return _result(rule, "PASS", "A Summary Compensation Table section is present in the latest proxy.", "high",
                       False, evidence)
    return _result(rule, "POTENTIAL_GAP", "No Summary Compensation Table section detected; it may appear under another heading.",
                   "medium", True)


def check_pvp(rule: Rule, facts: Facts):
    proxy = facts.latest_proxy()
    if proxy is None:
        return _result(rule, "INSUFFICIENT_EVIDENCE", "No proxy statement available.", "low", True)
    if proxy["filing_date"] < date(2023, 1, 1):
        return NotApplicable(rule_id=rule.id, source=rule.source, title=rule.title,
                             reason=(f"Pay-versus-performance applies to fiscal years ending on or after "
                                     f"{PVP_FIRST_FISCAL_YEAR_END.isoformat()}; the latest proxy was filed "
                                     f"{proxy['filing_date'].isoformat()}."))
    if "pay_versus_performance" in facts.sections.get(proxy["accession_no"], set()):
        return _result(rule, "PASS", "A Pay versus Performance section is present in the latest proxy.", "high", False,
                       [Citation(accession_no=proxy["accession_no"], form=proxy["form"],
                                 filing_date=proxy["filing_date"].isoformat(), section="Pay versus Performance",
                                 quote="Pay versus Performance")])
    return _result(rule, "POTENTIAL_GAP", "No Pay versus Performance section detected in a proxy where it is required.",
                   "medium", True)


def check_rpt_policy(rule: Rule, facts: Facts):
    cite = _find(facts, "rpt_policy")
    if cite:
        return _result(rule, "PASS", "A related-person transaction review policy is described.", "high", False, [cite])
    proxy = facts.latest_proxy()
    if proxy and "related_person_transactions" in facts.sections.get(proxy["accession_no"], set()):
        return _result(rule, "POTENTIAL_GAP", "Related transactions section exists but no review policy sentence was found.",
                       "medium", True)
    return _result(rule, "INSUFFICIENT_EVIDENCE", "No related-person transactions section or policy found.", "low", True)


def check_rpt_amounts(rule: Rule, facts: Facts):
    if (missing := _no_relations(rule, facts)) is not None:
        return missing
    rows = facts.rows("RELATED_TRANSACTION")
    if not rows:
        return _result(rule, "INSUFFICIENT_EVIDENCE",
                       "No related-person transaction amounts were extracted; read the section manually.", "low", True)
    above = [r for r in rows if (parse_amount(r["props"].get("amount")) or 0) >= RELATED_PERSON_THRESHOLD_USD]
    listing = "; ".join(f"{r['person_name']} {r['props'].get('amount')}" for r in above) or "none above threshold"
    return _result(rule, "PASS",
                   f"{len(rows)} related-party items disclosed; {len(above)} at or above ${RELATED_PERSON_THRESHOLD_USD:,}: "
                   f"{listing}. Materiality and approval need human review.",
                   "medium", True, [_cite_row(r) for r in (above or rows)])


def check_independence(rule: Rule, facts: Facts):
    cite = _find(facts, "independence")
    if cite:
        return _result(rule, "PASS", "The board's director independence determination is disclosed.", "high", False, [cite])
    return _result(rule, "INSUFFICIENT_EVIDENCE", "No independence determination sentence found.", "low", True)


def check_financial_expert(rule: Rule, facts: Facts):
    cite = _find(facts, "financial_expert")
    if cite:
        return _result(rule, "PASS", "An audit committee financial expert is identified.", "high", False, [cite])
    if facts.latest_proxy() or facts.latest("10-K"):
        return _result(rule, "POTENTIAL_GAP",
                       "No audit committee financial expert statement found in the latest proxy and 10-K.", "medium", True)
    return _result(rule, "INSUFFICIENT_EVIDENCE", "No proxy or 10-K available.", "low", True)


def check_risk_oversight(rule: Rule, facts: Facts):
    cite = _find(facts, "risk_oversight")
    if cite:
        return _result(rule, "PASS", "The board's role in risk oversight is described.", "high", False, [cite])
    return _result(rule, "INSUFFICIENT_EVIDENCE", "No description of the board's role in risk oversight found.", "low", True)


def check_risk_committee(rule: Rule, facts: Facts):
    from app.rules.sector import is_financial

    rows = [r for r in facts.rows("MEMBER_OF") if "risk" in r["org_name"].lower()]
    if rows:
        names = sorted({r["org_name"] for r in rows})
        from_table = any(r["props"].get("from_table") for r in rows)
        return _result(rule, "PASS", f"Risk committee(s) identified: {', '.join(names)}.",
                       "medium" if from_table else "high", from_table, [_cite_row(r) for r in rows[:2]])
    if is_financial(facts.cik) is False:
        fields = {"rule_id": rule.id, "title": rule.title, "category": rule.category, "source": rule.source,
                  "reason": "A dedicated board risk committee is a financial-sector best practice (required for "
                            "large bank holding companies); this company's SEC industry code (SIC) is outside "
                            "finance (6000-6799) and no risk committee is disclosed."}
        return NotApplicable(**{k: v for k, v in fields.items() if k in NotApplicable.model_fields})
    if (missing := _no_relations(rule, facts)) is not None:
        return missing
    return _result(rule, "INSUFFICIENT_EVIDENCE", "No risk committee membership extracted.", "low", True)


def check_risk_leadership_change(rule: Rule, facts: Facts):
    proxy = facts.latest_proxy()
    if proxy is None:
        return _result(rule, "INSUFFICIENT_EVIDENCE", "No proxy statement available on or before the analysis date.",
                       "low", True)
    pattern = re.compile(RULE_PATTERNS["risk_leadership_change"], re.I | re.S)
    for p in facts.passages.get("risk_leadership_change", []):
        flat = " ".join(str(p.text).split())
        m = pattern.search(flat)
        if not m:
            continue
        start, end = max(0, m.start() - 120), min(len(flat), m.end() + 120)
        quote = ("..." if start else "") + flat[start:end] + ("..." if end < len(flat) else "")
        return _result(rule, "POTENTIAL_GAP",
                       f"A change, departure or vacancy in the Chief Risk Officer or Chief Financial Officer role is "
                       f"disclosed ({p.form} p.{p.page}). Check how long the role was unfilled and who covered it.",
                       "medium", True,
                       [Citation(accession_no=p.accession_no, form=p.form, filing_date=p.filing_date,
                                 section=p.section, page=p.page, chunk_id=p.chunk_id, quote=quote)])
    return _result(rule, "PASS", "No change or vacancy in the Chief Risk Officer or Chief Financial Officer role is "
                   "disclosed in the latest proxy or 10-K.", "medium", False)


def check_cro(rule: Rule, facts: Facts):
    from app.rules.sector import is_financial

    if is_financial(facts.cik) is False:
        fields = {"rule_id": rule.id, "title": rule.title, "category": rule.category, "source": rule.source,
                  "reason": "A designated Chief Risk Officer is a financial-sector best practice; this company's "
                            "SEC industry code (SIC) is outside finance (6000-6799)."}
        return NotApplicable(**{k: v for k, v in fields.items() if k in NotApplicable.model_fields})
    if (missing := _no_relations(rule, facts)) is not None:
        return missing
    proxy = facts.latest_proxy()
    pattern = re.compile(r"chief risk officer", re.I)
    rows = [r for r in facts.rows("OFFICER_OF")
            if pattern.search(r["props"].get("title") or "") or pattern.search(r["props"].get("quote") or "")]
    if rows:
        return _result(rule, "PASS",
                       f"Chief Risk Officer identified ({rows[0]['person_name']}) as of the proxy filed "
                       f"{proxy['filing_date'].isoformat()}; later changes are not visible in this filing.",
                       "high", False, [_cite_row(rows[0])])
    return _result(rule, "POTENTIAL_GAP", "No Chief Risk Officer identified among extracted executive officers.",
                   "medium", True)


def check_freshness(rule: Rule, facts: Facts):
    proxy = facts.latest_proxy()
    if proxy is None:
        return _result(rule, "INSUFFICIENT_EVIDENCE", "No proxy statement available on or before the analysis date.", "low", True)
    age = (facts.as_of - proxy["filing_date"]).days
    evidence = [Citation(accession_no=proxy["accession_no"], form=proxy["form"], filing_date=proxy["filing_date"].isoformat(),
                         quote=f"{proxy['form']} filed {proxy['filing_date'].isoformat()}")]
    if age > STALE_PROXY_DAYS:
        return _result(rule, "POTENTIAL_GAP",
                       f"Latest governance disclosure is {age} days old at the analysis date; board and officer facts may be outdated.",
                       "high", True, evidence)
    return _result(rule, "PASS", f"Latest proxy is {age} days old at the analysis date (annual cycle).", "high", False, evidence)


def check_yoy(rule: Rule, facts: Facts):
    tenk = facts.latest("10-K")
    rows = [r for r in facts.yoy if r.get("prev_chars")]
    if tenk is None or not rows:
        return _result(rule, "INSUFFICIENT_EVIDENCE", "Fewer than two 10-K filings available for comparison.", "low", True)
    flagged = [r for r in rows if r["section_key"] in RISK_SECTIONS and r["change_pct"] is not None
               and abs(r["change_pct"]) >= YOY_FLAG_PCT and max(r["chars"], r["prev_chars"]) >= YOY_MIN_CHARS]
    if flagged:
        text = "; ".join(f"{r['title']} {r['prev_chars']:,} -> {r['chars']:,} chars ({r['change_pct']:+.1f}%)" for r in flagged)
        return _result(rule, "POTENTIAL_GAP",
                       f"Large year-over-year change in risk-related disclosure: {text}. Read both versions; may be reorganisation.",
                       "medium", True,
                       [Citation(accession_no=tenk["accession_no"], form="10-K", filing_date=tenk["filing_date"].isoformat(),
                                 section=r["title"], quote=r["title"]) for r in flagged])
    return _result(rule, "PASS", "No large year-over-year change in risk-related 10-K sections.", "high", False)


def check_officer_outside_roles(rule: Rule, facts: Facts):
    if (missing := _no_relations(rule, facts)) is not None:
        return missing
    officers = {r["person_key"] for r in facts.rows("OFFICER_OF")}
    seats = [r for r in facts.rows("BOARD_SEAT") if r["person_key"] in officers]
    if seats:
        listing = "; ".join(f"{r['person_name']} -> {r['org_name']}" for r in seats)
        return _result(rule, "POTENTIAL_GAP",
                       f"Executive officers hold outside board seats: {listing}. Potential conflict-of-interest questions to "
                       f"review; a disclosed relationship is not evidence of misconduct.",
                       "high", True, [_cite_row(r) for r in seats])
    return _result(rule, "PASS", "No outside board seats extracted for executive officers.", "medium", False)


def check_chair_consistency(rule: Rule, facts: Facts):
    if (missing := _no_relations(rule, facts)) is not None:
        return missing
    chairs: dict[str, list[dict]] = {}
    for r in facts.rows("MEMBER_OF"):
        if r["chair"]:
            chairs.setdefault(r["org_name"], []).append(r)
    multiple = {k: v for k, v in chairs.items() if len({r["person_key"] for r in v}) > 1}
    if multiple:
        listing = "; ".join(f"{k}: {', '.join(sorted({r['person_name'] for r in v}))}" for k, v in multiple.items())
        return _result(rule, "POTENTIAL_GAP",
                       f"More than one chair recorded for: {listing}. Likely a table reading issue or a mid-year change; verify.",
                       "medium", True, [_cite_row(r) for v in multiple.values() for r in v])
    return _result(rule, "PASS", "Each committee has at most one recorded chair.", "medium", False)


RULES: list[Rule] = [
    Rule("R401_DIRECTORS", "Reg S-K Item 401(a)", "law", "Directors identified",
         "Identify each director, with the positions held.", ["director names with verified quotes"], check_directors),
    Rule("R401_OTHER_BOARDS", "Reg S-K Item 401(e)(2)", "law", "Other public company directorships",
         "Disclose other public company directorships held by each director.",
         ["sentence disclosing other directorships", "outside board seats"], check_other_boards),
    Rule("R402_SCT", "Reg S-K Item 402(c)", "law", "Summary Compensation Table",
         "Provide a Summary Compensation Table for named executive officers.", ["section in latest proxy"], check_sct),
    Rule("R402_PVP", "Reg S-K Item 402(v)", "law", "Pay versus performance",
         "Disclose the relationship between executive pay and company performance (when required).",
         ["section in latest proxy", "filing date for applicability"], check_pvp),
    Rule("R404_POLICY", "Reg S-K Item 404(b)", "law", "Related-person transaction policy",
         "Describe the policies and procedures for review and approval of related-person transactions.",
         ["sentence describing the policy"], check_rpt_policy),
    Rule("R404_TRANSACTIONS", "Reg S-K Item 404(a)", "law", "Related-person transactions above $120,000",
         "Disclose transactions above $120,000 in which a related person has a material interest.",
         ["extracted related-party items with amounts"], check_rpt_amounts),
    Rule("R407_INDEPENDENCE", "Reg S-K Item 407(a)", "law", "Director independence",
         "Identify which directors the board has determined to be independent.", ["independence determination sentence"],
         check_independence),
    Rule("R407_FIN_EXPERT", "Reg S-K Item 407(d)(5)", "law", "Audit committee financial expert",
         "Disclose whether the audit committee has at least one audit committee financial expert.",
         ["financial expert sentence in proxy or 10-K"], check_financial_expert),
    Rule("R407_RISK_OVERSIGHT", "Reg S-K Item 407(h)", "law", "Board leadership and risk oversight",
         "Describe the board leadership structure and the board's role in risk oversight.", ["risk oversight sentence"],
         check_risk_oversight),
    Rule("BP_RISK_COMMITTEE", "Governance best practice", "best_practice", "Dedicated risk committee",
         "A board committee dedicated to enterprise risk oversight.", ["committee memberships"], check_risk_committee),
    Rule("BP_CRO", "Governance best practice", "best_practice", "Chief Risk Officer identified",
         "A designated Chief Risk Officer among executive officers.", ["executive officer titles"], check_cro),
    Rule("II_RISK_LEADERSHIP_CHANGE", "Nirikkha internal indicator", "internal_indicator",
         "Risk leadership change or vacancy",
         "Flag a disclosed departure, transition or vacancy in the Chief Risk Officer or Chief Financial Officer role.",
         ["sentence in latest proxy or 10-K"], check_risk_leadership_change),
    Rule("II_DISCLOSURE_FRESHNESS", "Nirikkha internal indicator", "internal_indicator", "Governance disclosure freshness",
         "The latest proxy should not be older than about 15 months at the analysis date.", ["proxy filing date"],
         check_freshness),
    Rule("II_YOY_CHANGE", "Nirikkha internal indicator", "internal_indicator", "Year-over-year disclosure change",
         "Flag large changes (>= 25%) in risk-related 10-K sections for review.", ["DuckDB section sizes"], check_yoy),
    Rule("II_OFFICER_OUTSIDE_ROLES", "Nirikkha internal indicator", "internal_indicator", "Executive outside board seats",
         "Flag outside board seats held by executive officers as potential conflict questions.",
         ["graph: officer board seats"], check_officer_outside_roles),
    Rule("II_COMMITTEE_CHAIR_CONSISTENCY", "Nirikkha internal indicator", "internal_indicator", "Committee chair consistency",
         "Each committee should have one chair in a disclosure; more than one needs verification.",
         ["graph: committee chairs"], check_chair_consistency),
]


def evaluate(facts: Facts, rules: list[Rule] | None = None) -> dict:
    results: list[RuleResult] = []
    not_applicable: list[NotApplicable] = []
    for rule in rules or RULES:
        outcome = rule.check(rule, facts)
        (not_applicable if isinstance(outcome, NotApplicable) else results).append(outcome)
    summary = {
        "by_result": dict(Counter(r.result for r in results)),
        "by_category": {cat: dict(Counter(r.result for r in results if r.category == cat))
                        for cat in ("law", "best_practice", "internal_indicator")},
        "human_review": sum(1 for r in results if r.human_review),
        "not_applicable": len(not_applicable),
    }
    return {"company": facts.company, "cik": facts.cik, "as_of": facts.as_of.isoformat(), "summary": summary,
            "results": [r.model_dump() for r in results], "not_applicable": [n.model_dump() for n in not_applicable]}