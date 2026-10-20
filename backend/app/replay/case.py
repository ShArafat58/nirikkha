"""First Warning Sign Replay: case file, validation and evidence freeze.

A replay case is a JSON file with a timeline of dated events and a list of
documented warning signs. Every event has two dates:
  event_date  - when it happened
  public_date - when the public could first know about it
Only events with public_date <= freeze_date are visible to the system.
A warning sign may only cite visible events as pre-freeze evidence
(the hindsight guard).
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import date
from pathlib import Path
from typing import Any

BACKEND_DIR = Path(__file__).resolve().parents[2]
CASES_DIR = BACKEND_DIR / "data" / "replay"

KINDS = {"filing", "disclosure", "market", "regulatory", "outcome", "review"}
PRECISIONS = {"day", "month"}
EVENT_FIELDS = ("id", "kind", "precision", "event_date", "public_date", "title", "sources")
SIGN_FIELDS = ("id", "category", "statement", "pre_freeze_evidence", "confirmed_by", "keywords")
CASE_FIELDS = ("id", "company", "cik", "freeze_date", "outcome_date", "outcome", "timeline", "warning_signs")


class CaseError(ValueError):
    """Raised when a replay case file is missing or invalid."""


def _date(value: Any, where: str, errors: list[str]) -> date | None:
    try:
        return date.fromisoformat(str(value))
    except ValueError:
        errors.append(f"{where}: bad date {value!r}")
        return None


def _check_sources(sources: Any, where: str, errors: list[str]) -> None:
    if not isinstance(sources, list) or not sources:
        errors.append(f"{where}: needs at least one source")
        return
    for src in sources:
        if not isinstance(src, dict) or not src.get("title") or not str(src.get("url", "")).startswith("https://"):
            errors.append(f"{where}: every source needs a title and an https url")


def validate(case: dict) -> None:
    """Raise CaseError listing every problem in the case file."""
    errors: list[str] = []
    missing = [f for f in CASE_FIELDS if f not in case]
    if missing:
        raise CaseError(f"case missing fields: {missing}")

    freeze = _date(case["freeze_date"], "freeze_date", errors)
    outcome = _date(case["outcome_date"], "outcome_date", errors)
    if freeze and outcome and not freeze < outcome:
        errors.append("freeze_date must be before outcome_date")

    events: dict[str, dict] = {}
    for i, ev in enumerate(case["timeline"]):
        absent = [f for f in EVENT_FIELDS if f not in ev]
        if absent:
            errors.append(f"timeline[{i}]: missing {absent}")
            continue
        where = f"event {ev['id']}"
        if ev["id"] in events:
            errors.append(f"{where}: duplicate id")
        if ev["kind"] not in KINDS:
            errors.append(f"{where}: unknown kind {ev['kind']!r}")
        if ev["precision"] not in PRECISIONS:
            errors.append(f"{where}: unknown precision {ev['precision']!r}")
        happened = _date(ev["event_date"], where, errors)
        public = _date(ev["public_date"], where, errors)
        if happened and public and public < happened:
            errors.append(f"{where}: public_date before event_date")
        _check_sources(ev["sources"], where, errors)
        events[ev["id"]] = ev

    seen: set[str] = set()
    for i, sign in enumerate(case["warning_signs"]):
        absent = [f for f in SIGN_FIELDS if f not in sign]
        if absent:
            errors.append(f"warning_signs[{i}]: missing {absent}")
            continue
        where = f"sign {sign['id']}"
        if sign["id"] in seen:
            errors.append(f"{where}: duplicate id")
        seen.add(sign["id"])
        for ref in sign["pre_freeze_evidence"]:
            ev = events.get(ref)
            if ev is None:
                errors.append(f"{where}: unknown pre_freeze_evidence {ref!r}")
            elif freeze and str(ev["public_date"]) > freeze.isoformat():
                errors.append(f"{where}: {ref} became public after the freeze (hindsight)")
        for ref in sign["confirmed_by"]:
            if ref not in events:
                errors.append(f"{where}: unknown confirmed_by {ref!r}")
        if not sign["confirmed_by"]:
            errors.append(f"{where}: needs at least one confirmed_by event")

    if errors:
        raise CaseError("; ".join(errors))


def load_case(case_id: str) -> dict:
    path = CASES_DIR / case_id / "case.json"
    if not path.exists():
        raise CaseError(f"replay case not found: {case_id}")
    try:
        case = json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError as exc:
        raise CaseError(f"case {case_id} is not valid JSON: {exc}") from exc
    validate(case)
    return case


def is_visible(event: dict, case: dict) -> bool:
    return str(event["public_date"]) <= str(case["freeze_date"])


def visible_events(case: dict) -> list[dict]:
    return [ev for ev in case["timeline"] if is_visible(ev, case)]


def frozen_events(case: dict) -> list[dict]:
    return [ev for ev in case["timeline"] if not is_visible(ev, case)]


def is_knowable(sign: dict) -> bool:
    """A sign is knowable only if some pre-freeze public evidence exists for it."""
    return bool(sign["pre_freeze_evidence"])


def evidence_window(case: dict, filings: list[dict]) -> tuple[list[dict], list[dict]]:
    """Split filings into (allowed, excluded) by filing_date vs the freeze date."""
    freeze = str(case["freeze_date"])
    allowed = [f for f in filings if str(f["filing_date"])[:10] <= freeze]
    excluded = [f for f in filings if str(f["filing_date"])[:10] > freeze]
    return allowed, excluded


def _user_agent() -> str:
    ua = os.getenv("SEC_USER_AGENT", "")
    env = BACKEND_DIR / ".env"
    if not ua and env.exists():
        for line in env.read_text(encoding="utf-8-sig").splitlines():
            if line.startswith("SEC_USER_AGENT="):
                ua = line.split("=", 1)[1].strip().strip('"').strip("'")
                break
    return ua or "Nirikkha replay link check"


def check_links(case: dict) -> list[tuple[str, str]]:
    """Return (url, result) for every unique source url. result: ok / manual / fail:<why>."""
    import httpx

    urls: list[str] = []
    for ev in case["timeline"]:
        for src in ev["sources"]:
            if src["url"] not in urls:
                urls.append(src["url"])
    results: list[tuple[str, str]] = []
    with httpx.Client(follow_redirects=True, timeout=20, headers={"User-Agent": _user_agent()}) as client:
        for url in urls:
            try:
                code = client.get(url).status_code
                if code == 200:
                    results.append((url, "ok"))
                elif code in (401, 403, 429):
                    results.append((url, f"manual ({code}, open in browser)"))
                else:
                    results.append((url, f"fail:{code}"))
            except httpx.HTTPError as exc:
                results.append((url, f"fail:{type(exc).__name__}"))
            time.sleep(0.25)  # stay well under SEC's request rate limit
    return results


def main() -> int:
    parser = argparse.ArgumentParser(description="Show and check a replay case")
    parser.add_argument("case_id")
    parser.add_argument("--check-links", action="store_true")
    args = parser.parse_args()
    try:
        case = load_case(args.case_id)
    except CaseError as exc:
        print(f"INVALID: {exc}")
        return 1

    print(f"{case['company']}  freeze {case['freeze_date']}  outcome {case['outcome_date']}")
    print("-" * 78)
    for ev in sorted(case["timeline"], key=lambda e: e["public_date"]):
        tag = "[open]  " if is_visible(ev, case) else "[frozen]"
        print(f"{tag} public {ev['public_date']}  {ev['kind']:<10} {ev['title'][:52]}")
    print("-" * 78)
    for sign in case["warning_signs"]:
        tag = "knowable" if is_knowable(sign) else "NOT knowable from public evidence"
        print(f"{sign['id']:<26} {tag}")
    knowable = sum(is_knowable(s) for s in case["warning_signs"])
    print(f"\nvisible events {len(visible_events(case))}, frozen {len(frozen_events(case))}, "
          f"signs knowable {knowable}/{len(case['warning_signs'])}")

    if args.check_links:
        print("\nlinks:")
        failed = 0
        for url, result in check_links(case):
            failed += result.startswith("fail")
            print(f"  {result:<12} {url}")
        if failed:
            print(f"{failed} link(s) failed")
            return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())