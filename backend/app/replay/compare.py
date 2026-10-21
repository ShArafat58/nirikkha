"""First Warning Sign Replay, step 5: compare a frozen-evidence run with the known outcome.

Deterministic, no LLM. Works on any report shape: it walks the report JSON and
collects findings (dicts with a "citations" list) and rule results (dicts with
"rule_id" and a known "result").

Each documented warning sign gets one status:
  detected      - a finding matches >= 2 distinct keywords, or a linked rule is GAP/FAIL
  partial       - one keyword matches, or a linked rule says INSUFFICIENT_EVIDENCE
  missed        - knowable before the freeze, but nothing matched
  not_knowable  - no public evidence existed before the freeze, and nothing matched
Any citation to a filing outside the frozen evidence set makes the replay INVALID.

    python -m app.replay.compare svb --job e3d02af1
    python -m app.replay.compare svb --report path/to/report.json
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from typing import Any, Iterator

from app.replay.case import CASES_DIR, CaseError, frozen_events, is_knowable, load_case

RESULTS = {"PASS", "POTENTIAL_GAP", "FAIL", "INSUFFICIENT_EVIDENCE"}
FLAG = {"POTENTIAL_GAP", "FAIL"}
OPEN = {"INSUFFICIENT_EVIDENCE"}
SKIP_KEYS = {"id", "chunk_id", "accession_no", "url", "filing_date"}


def _dicts(node: Any) -> Iterator[dict]:
    if isinstance(node, dict):
        yield node
        for v in node.values():
            yield from _dicts(v)
    elif isinstance(node, list):
        for v in node:
            yield from _dicts(v)


def _strings(node: Any) -> Iterator[str]:
    if isinstance(node, str):
        yield node
    elif isinstance(node, dict):
        for k, v in node.items():
            if k not in SKIP_KEYS:
                yield from _strings(v)
    elif isinstance(node, list):
        for v in node:
            yield from _strings(v)


def _text(node: Any) -> str:
    return " ".join(_strings(node)).lower()


def _key(d: dict) -> str:
    return str(d.get("id") or json.dumps(d, sort_keys=True, default=str))


def collect(report: dict) -> tuple[list[dict], list[dict]]:
    """Return (findings, rule_results) found anywhere in the report, de-duplicated."""
    findings: dict[str, dict] = {}
    rules: dict[str, dict] = {}
    for d in _dicts(report):
        if isinstance(d.get("citations"), list):
            findings.setdefault(_key(d), d)
        elif isinstance(d.get("rule_id"), str) and d.get("result") in RESULTS:
            rules.setdefault(d["rule_id"], d)
    return list(findings.values()), list(rules.values())


def _title(f: dict) -> str:
    for k in ("title", "statement", "claim", "summary", "question"):
        if isinstance(f.get(k), str) and f[k].strip():
            return f[k].strip()
    return next(_strings(f), "(untitled finding)")


def _is_question(f: dict) -> bool:
    """True when the item is an open question the system raised, not a flagged finding."""
    title = _title(f).lower()
    return bool(f.get("decision_question")) or title.startswith("decision question") or title.endswith("?")


def _hits(keywords: list[str], text: str) -> list[str]:
    return [k for k in keywords if re.search(r"\b" + re.escape(k.lower()), text)]


def _rule_links(sign: dict) -> list[tuple[str, str | None]]:
    out = []
    for entry in sign.get("rules", []):
        rule_id, _, need = entry.partition(":")
        out.append((rule_id, need or None))
    return out


def find_leaks(case: dict, findings: list[dict], allowed: set[str] | None) -> list[dict]:
    freeze = str(case["freeze_date"])
    leaks = []
    for f in findings:
        for c in f.get("citations") or []:
            if not isinstance(c, dict):
                continue
            acc = c.get("accession_no")
            filed = str(c.get("filing_date") or "")[:10]
            if (allowed is not None and acc and acc not in allowed) or (filed and filed > freeze):
                leaks.append({"finding": _title(f)[:120], "accession_no": acc, "filing_date": filed or None})
    return leaks


def run_as_of(report: dict) -> str | None:
    """The analysis date the run used, if the report records one."""
    for key in ("as_of", "freeze_date"):
        if isinstance(report.get(key), str) and report[key]:
            return report[key][:10]
    return None


def compare(case: dict, report: dict, allowed_accessions: set[str] | None = None) -> dict:
    findings, rules = collect(report)
    by_rule = {r["rule_id"]: r for r in rules}
    texts = [(f, _text(f)) for f in findings]
    matched: set[str] = set()
    signs = []

    for sign in case["warning_signs"]:
        scored = []
        for f, text in texts:
            hit = _hits(sign["keywords"], text)
            if hit:
                scored.append((len(hit), hit, f))
        scored.sort(key=lambda x: -x[0])

        rule_hits = []
        for rule_id, need in _rule_links(sign):
            r = by_rule.get(rule_id)
            if r and r["result"] in FLAG | OPEN and (need is None or need.lower() in _text(r)):
                rule_hits.append(r)

        strong = [s for s in scored if s[0] >= 2]
        flagged = [s for s in strong if not _is_question(s[2])]
        if flagged or any(r["result"] in FLAG for r in rule_hits):
            status = "detected"
        elif strong:
            status = "questioned"
        elif scored or rule_hits:
            status = "partial"
        else:
            status = "missed" if is_knowable(sign) else "not_knowable"

        shown = strong[:3] or scored[:1]
        for _, _, f in shown:
            matched.add(_key(f))
        signs.append({
            "id": sign["id"],
            "category": sign["category"],
            "statement": sign["statement"],
            "knowable_before_freeze": is_knowable(sign),
            "status": status,
            "evidence": [{
                "finding": _title(f)[:200],
                "type": "question" if _is_question(f) else "finding",
                "matched_keywords": hit,
                "citations": [
                    {k: c.get(k) for k in ("form", "accession_no", "page", "section")}
                    | {"quote": str(c.get("quote") or "")[:240]}
                    for c in (f.get("citations") or [])[:2] if isinstance(c, dict)
                ],
            } for _, hit, f in shown],
            "rules": [{"rule_id": r["rule_id"], "result": r["result"],
                       "rationale": str(r.get("rationale") or "")[:240]} for r in rule_hits],
            "confirmed_by": sign["confirmed_by"],
        })

    knowable = [s for s in signs if s["knowable_before_freeze"]]
    count = {st: sum(1 for s in signs if s["status"] == st)
             for st in ("detected", "questioned", "partial", "missed", "not_knowable")}
    leaks = find_leaks(case, findings, allowed_accessions)
    as_of = run_as_of(report)
    if as_of and as_of > str(case["freeze_date"]):
        leaks.insert(0, {"finding": f"run analysed as of {as_of}, after the freeze date",
                         "accession_no": None, "filing_date": as_of})
    other = [_title(f)[:160] for f in findings if _key(f) not in matched]
    return {
        "case_id": case["id"],
        "company": case["company"],
        "freeze_date": case["freeze_date"],
        "outcome_date": case["outcome_date"],
        "outcome": case["outcome"],
        "run_as_of": as_of,
        "verdict": "INVALID: uses evidence or an analysis date outside the frozen window" if leaks else "VALID",
        "leaks": leaks,
        "summary": {
            **count,
            "signs": len(signs),
            "knowable": len(knowable),
            "detection_rate": round(count["detected"] / len(knowable), 2) if knowable else None,
            "flagged_or_questioned_rate": round(
                sum(s["status"] in ("detected", "questioned") for s in knowable) / len(knowable), 2) if knowable else None,
            "detection_rate_incl_partial": round(
                sum(s["status"] in ("detected", "questioned", "partial") for s in knowable) / len(knowable), 2) if knowable else None,
            "findings_in_report": len(findings),
            "other_signals": len(other),
        },
        "signs": signs,
        "other_signals": other[:15],
        "frozen_out": [{"public_date": e["public_date"], "title": e["title"]} for e in frozen_events(case)],
    }


def _load_job(prefix: str, cik: str, freeze: str) -> tuple[str, dict, set[str]]:
    from app.db import connect

    with connect() as conn:
        row = conn.execute(
            "select id::text, report from crash_tests where id::text like %s and report is not null limit 1",
            (prefix + "%",),
        ).fetchone()
        if not row:
            raise LookupError(f"no finished crash-test with id starting {prefix!r}")
        allowed = {r[0] for r in conn.execute(
            "select accession_no from filings where cik = %s and filing_date <= %s", (cik, freeze)).fetchall()}
    report = row[1] if isinstance(row[1], dict) else json.loads(row[1])
    return row[0], report, allowed


def main() -> int:
    parser = argparse.ArgumentParser(description="Compare a crash-test with a replay case")
    parser.add_argument("case_id")
    src = parser.add_mutually_exclusive_group(required=True)
    src.add_argument("--job", help="crash-test id (prefix is enough)")
    src.add_argument("--report", help="path to a report JSON file")
    parser.add_argument("--publish", action="store_true", help="also save as data/replay/<case>/result.json")
    args = parser.parse_args()

    try:
        case = load_case(args.case_id)
        if args.job:
            job_id, report, allowed = _load_job(args.job, case["cik"], case["freeze_date"])
        else:
            job_id, allowed = args.report, None
            with open(args.report, encoding="utf-8-sig") as fh:
                report = json.load(fh)
    except (CaseError, LookupError, OSError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}")
        return 1
    except Exception as exc:  # database errors
        print(f"ERROR: could not load the crash-test: {exc}")
        return 1

    result = compare(case, report, allowed)
    result["source"] = job_id

    from app.config import get_settings

    out_dir = get_settings().cache_dir / "replay"
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / f"{case['id']}_{str(job_id).split('/')[-1].split(chr(92))[-1][:12]}.json"
    out.write_text(json.dumps(result, indent=1, default=str), encoding="utf-8")
    if args.publish:
        if result["verdict"] != "VALID":
            print("not published: replay is INVALID")
        else:
            published = CASES_DIR / case["id"] / "result.json"
            published.write_text(json.dumps(result, indent=1, default=str) + "\n", encoding="utf-8")
            print(f"published: {published}")

    s = result["summary"]
    print(f"{result['company']}  freeze {result['freeze_date']}  source {job_id}")
    print(f"verdict: {result['verdict']}")
    for leak in result["leaks"][:5]:
        print(f"  LEAK {leak}")
    print("-" * 78)
    for sign in result["signs"]:
        print(f"[{sign['status']:<12}] {sign['id']:<26} {sign['statement'][:44]}")
        for ev in sign["evidence"][:1]:
            print(f"               finding: {ev['finding'][:70]}  keywords={ev['matched_keywords']}")
        for r in sign["rules"]:
            print(f"               rule: {r['rule_id']} {r['result']}")
    print("-" * 78)
    print(f"detected {s['detected']}, questioned {s['questioned']}, partial {s['partial']}, missed {s['missed']}, "
          f"not knowable {s['not_knowable']}  |  detection rate {s['detection_rate']} "
          f"(with questions {s['flagged_or_questioned_rate']}, incl. partial {s['detection_rate_incl_partial']}) of {s['knowable']} knowable signs")
    print(f"other signals in the report (not in the documented outcome): {s['other_signals']}")
    print(f"saved: {out}")
    return 0 if result["verdict"] == "VALID" else 2


if __name__ == "__main__":
    sys.exit(main())