"""Replay API: replay cases and their published comparison results.

Read-only and public: everything here comes from public filings and public
reports, and results are precomputed files, so no database is needed.
"""
from __future__ import annotations

import json
import re

from fastapi import APIRouter, HTTPException

from app.replay.case import CASES_DIR, CaseError, is_visible, load_case

router = APIRouter(prefix="/api/replay", tags=["replay"])
_CASE_ID = re.compile(r"^[a-z0-9-]{1,40}$")
CASE_FIELDS = ("id", "company", "cik", "freeze_date", "outcome_date", "outcome", "freeze_rationale")


def _result(case_id: str, name: str = "result.json") -> dict | None:
    path = CASES_DIR / case_id / name
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError:
        return None


@router.get("")
def list_cases() -> dict:
    cases = []
    if CASES_DIR.exists():
        for folder in sorted(CASES_DIR.iterdir()):
            if not (folder / "case.json").exists():
                continue
            try:
                case = load_case(folder.name)
            except CaseError:
                continue
            result = _result(folder.name)
            cases.append({k: case.get(k) for k in CASE_FIELDS} | {
                "has_result": result is not None,
                "summary": result["summary"] if result else None,
            })
    return {"cases": cases}


@router.get("/{case_id}")
def get_case(case_id: str) -> dict:
    if not _CASE_ID.match(case_id):
        raise HTTPException(status_code=404, detail="Replay case not found.")
    try:
        case = load_case(case_id)
    except CaseError:
        raise HTTPException(status_code=404, detail="Replay case not found.")
    timeline = [ev | {"visible_at_freeze": is_visible(ev, case)}
                for ev in sorted(case["timeline"], key=lambda e: e["public_date"])]
    return {
        "case": {k: case.get(k) for k in CASE_FIELDS} | {
            "timeline": timeline,
            "warning_signs": case["warning_signs"],
        },
        "result": _result(case_id),
        "controls": _result(case_id, "controls.json"),
    }