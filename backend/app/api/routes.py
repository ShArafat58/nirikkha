"""Nirikkha REST API (polling).

POST /api/crash-tests              start a Crash-Test, or return the cached result for the same company, date and decision
GET  /api/crash-tests/{id}         status, per-node events (live progress) and, when done, the full report
POST /api/crash-tests/{id}/memo    create (or return the cached) legal memo for a finished Crash-Test
GET  /api/crash-tests/{id}/memo    the cached legal memo
GET  /api/companies                companies with loaded filings and their latest finished Crash-Tests
GET  /api/evaluation               latest evaluation results (python -m evaluation.run)

The decision text is whitespace-normalized and PII-redacted BEFORE it is hashed, stored or sent to any model.
Only one live run at a time (free-tier memory and token limits); a busy server answers 429 with a clear message.
"""

from __future__ import annotations

import hashlib
import json
import re
import uuid
from datetime import date, datetime, timedelta, timezone
from functools import lru_cache
from typing import Any, Callable

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Response
from pydantic import BaseModel, Field

from app.agents.memo import to_markdown
from app.config import BACKEND_DIR, get_settings
from app.db import DatabaseError
from app.guardrails.pii import redact_pii

router = APIRouter(prefix="/api")

PIPELINE = ["redact", "guard", "collect", "plan", "gather", "analyze", "relationship", "consistency", "regulatory",
            "missing_evidence", "merge", "sentinel", "score"]
STALE_AFTER = timedelta(minutes=15)
MAX_DECISION_CHARS = 1500
EVALUATION_FILE = BACKEND_DIR / "evaluation" / "results.json"

Runner = Callable[[str, date, str, Callable[[list[dict]], None]], dict]
MemoWriter = Callable[[dict], dict]


class CrashTestRequest(BaseModel):
    cik: str = Field(..., min_length=1, max_length=13, examples=["719739"])
    as_of: date | None = Field(None, description="Evidence freeze date: filings after it are invisible. Default today.")
    decision: str = Field("", max_length=MAX_DECISION_CHARS,
                          examples=["Before we proceed with a deposit partnership with this bank, identify the "
                                    "governance risks and evidence gaps we should investigate."])


class CrashTestStarted(BaseModel):
    id: str
    status: str
    cached: bool


def normalize_cik(raw: str) -> str:
    digits = re.sub(r"\D", "", raw)
    if not digits or len(digits) > 10:
        raise HTTPException(422, "cik must be 1 to 10 digits (SEC Central Index Key).")
    return digits.zfill(10)


def decision_key(decision: str) -> tuple[str, str]:
    redacted, _ = redact_pii(" ".join(decision.split()))
    return redacted, hashlib.sha256(redacted.lower().encode("utf-8")).hexdigest()[:16]


@lru_cache
def get_store():
    from app.api.store import PostgresStore
    return PostgresStore()


def graph_runner(cik: str, as_of: date, decision: str, on_event: Callable[[list[dict]], None]) -> dict:
    """Runs the LangGraph Crash-Test node by node and reports each node's events as it finishes."""
    from app.agents.graph import build_graph, default_services

    app = build_graph(default_services())
    initial = {"cik": cik, "as_of": as_of.isoformat(), "decision": decision, "findings": [], "events": [], "usage": []}
    final: dict[str, Any] = {}
    for chunk in app.stream(initial, stream_mode="updates"):
        for update in chunk.values():
            if not isinstance(update, dict):
                continue
            for key in ("allowed", "guard_result", "report"):
                if key in update:
                    final[key] = update[key]
            if update.get("events"):
                on_event(update["events"])
    return final


def get_runner() -> Runner:
    return graph_runner


def get_memo_writer() -> MemoWriter:
    def write(report: dict) -> dict:
        from app.agents.memo import draft_memo
        from app.llm.client import get_llm
        return draft_memo(report, get_llm().complete)
    return write


def execute(job_id: str, cik: str, as_of: date, decision: str, store: Any, runner: Runner) -> None:
    events: list[dict] = []

    def on_event(new: list[dict]) -> None:
        events.extend(new)
        store.update(job_id, status="running", events=events)

    try:
        store.update(job_id, status="running")
        state = runner(cik, as_of, decision, on_event)
        if state.get("allowed") is False:
            reason = (state.get("guard_result") or {}).get("reason") or "input guard"
            store.update(job_id, status="blocked", events=events, error=f"Blocked by the input guard: {reason}")
        elif state.get("report"):
            mode = "hybrid + cross-encoder rerank" if get_settings().rerank_enabled else "hybrid (reranker disabled on this server)"
            store.update(job_id, status="done", events=events, report={**state["report"], "retrieval_mode": mode})
        else:
            store.update(job_id, status="failed", events=events, error="The Crash-Test produced no report.")
    except Exception as exc:  # last resort: a job must never stay "running" forever
        message = f"{type(exc).__name__}: {str(exc).strip().splitlines()[0] if str(exc).strip() else ''}"[:300]
        try:
            store.update(job_id, status="failed", events=events, error=message)
        except Exception:
            pass


def _row(store: Any, job_id: str) -> dict:
    try:
        uuid.UUID(job_id)
    except ValueError:
        raise HTTPException(404, "Crash-Test not found.")
    try:
        row = store.get(job_id)
    except DatabaseError as exc:
        raise HTTPException(503, f"Database unavailable: {exc}") from exc
    if not row:
        raise HTTPException(404, "Crash-Test not found.")
    return dict(row)


@router.post("/crash-tests", response_model=CrashTestStarted, status_code=202, tags=["crash-tests"],
             summary="Start a Crash-Test (or return the cached one)")
def start_crash_test(req: CrashTestRequest, background: BackgroundTasks, response: Response,
                     store: Any = Depends(get_store), runner: Runner = Depends(get_runner)) -> CrashTestStarted:
    cik = normalize_cik(req.cik)
    as_of = req.as_of or date.today()
    if as_of > date.today():
        raise HTTPException(422, "as_of cannot be in the future.")
    decision, key = decision_key(req.decision)
    try:
        cached = store.find_done(cik, as_of, key)
        if cached:
            response.status_code = 200
            return CrashTestStarted(id=cached["id"], status="done", cached=True)
        if store.busy():
            raise HTTPException(429, "Another live Crash-Test is running. Try again in a minute, or open a precomputed demo.")
        job_id = store.create(cik, as_of, decision, key)
    except DatabaseError as exc:
        raise HTTPException(503, f"Database unavailable: {exc}") from exc
    background.add_task(execute, job_id, cik, as_of, decision, store, runner)
    return CrashTestStarted(id=job_id, status="queued", cached=False)


@router.get("/crash-tests/{job_id}", tags=["crash-tests"],
            summary="Poll a Crash-Test: status, live node events, report when done")
def get_crash_test(job_id: str, store: Any = Depends(get_store)) -> dict:
    row = _row(store, job_id)
    if row["status"] in ("queued", "running") and datetime.now(timezone.utc) - row["updated_at"] > STALE_AFTER:
        row["status"], row["error"] = "failed", "Timed out: no progress for 15 minutes."
        store.update(job_id, status="failed", error=row["error"])
    row["pipeline"] = PIPELINE
    row["done_nodes"] = sorted({e.get("node") for e in row.get("events") or [] if e.get("node")},
                               key=lambda n: PIPELINE.index(n) if n in PIPELINE else 99)
    return row


@router.post("/crash-tests/{job_id}/memo", tags=["legal memo"],
             summary="Create (or return the cached) legal memo for a finished Crash-Test")
def create_memo(job_id: str, store: Any = Depends(get_store), writer: MemoWriter = Depends(get_memo_writer)) -> dict:
    row = _row(store, job_id)
    if row["status"] != "done" or not row.get("report"):
        raise HTTPException(409, f"The Crash-Test is not finished (status: {row['status']}).")
    if row.get("memo"):
        return {"cached": True, "memo": row["memo"], "markdown": to_markdown(row["memo"])}
    memo = writer(row["report"])
    if memo.get("status") != "unavailable":   # an unavailable model is retried next time, not cached
        try:
            store.update(job_id, memo=memo)
        except DatabaseError:
            pass
    return {"cached": False, "memo": memo, "markdown": to_markdown(memo)}


@router.get("/crash-tests/{job_id}/memo", tags=["legal memo"], summary="The cached legal memo")
def get_memo(job_id: str, store: Any = Depends(get_store)) -> dict:
    row = _row(store, job_id)
    if not row.get("memo"):
        raise HTTPException(404, "No memo yet. POST to this URL to create one.")
    return {"cached": True, "memo": row["memo"], "markdown": to_markdown(row["memo"])}


@router.get("/companies", tags=["companies"], summary="Companies with loaded filings and their latest Crash-Tests")
def list_companies(store: Any = Depends(get_store)) -> list[dict]:
    try:
        return store.companies()
    except DatabaseError as exc:
        raise HTTPException(503, f"Database unavailable: {exc}") from exc


@router.get("/evaluation", tags=["evaluation"], summary="Latest evaluation results")
def evaluation() -> dict:
    if not EVALUATION_FILE.exists():
        raise HTTPException(404, "No evaluation results yet. Run: python -m evaluation.run")
    return json.loads(EVALUATION_FILE.read_text(encoding="utf-8"))