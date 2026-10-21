"""Nirikkha REST API (polling).

POST /api/crash-tests              start a Crash-Test, or return the cached result for the same company, date and decision
GET  /api/crash-tests/{id}         status, per-node events (live progress) and, when done, the full report
POST /api/crash-tests/{id}/memo    create (or return the cached) legal memo for a finished Crash-Test
GET  /api/crash-tests/{id}/memo    the cached legal memo
GET  /api/companies                companies with loaded filings and their latest finished Crash-Tests
GET  /api/evaluation               latest evaluation results (python -m evaluation.run)
GET  /api/status                   live mode (inline or worker) and whether an analysis worker is online

Live modes: RUN_JOBS_INLINE=true runs the Crash-Test inside the API process. RUN_JOBS_INLINE=false (Render free,
512 MB) only queues it; `python -m app.api.worker` on a machine with enough memory runs it with the full pipeline.
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

import httpx

from app.agents.memo import to_markdown
from app.auth.deps import get_current_user, get_optional_user, get_user_store
from app.business.plans import monthly_limit, plan
from app.config import BACKEND_DIR, get_settings
from app.db import DatabaseError
from app.guardrails.pii import redact_pii

router = APIRouter(prefix="/api")

PIPELINE = ["redact", "guard", "collect", "plan", "gather", "analyze", "relationship", "consistency", "regulatory",
            "missing_evidence", "merge", "sentinel", "score"]
STALE_AFTER = timedelta(minutes=15)
QUEUE_TIMEOUT = timedelta(minutes=5)
MAX_DECISION_CHARS = 1500
EVALUATION_FILE = BACKEND_DIR / "evaluation" / "results.json"
NO_WORKER = ("No analysis worker picked up this Crash-Test within 5 minutes. Open a precomputed demo, "
             "or try again when the analysis worker is online.")
PRIVATE_UNAVAILABLE = "Private mode needs the local model runtime (Ollama). It is not running on this server."

Runner = Callable[[str, date, str, Callable[[list[dict]], None], bool], dict]
MemoWriter = Callable[[dict], dict]


class CrashTestRequest(BaseModel):
    cik: str = Field(..., min_length=1, max_length=13, examples=["719739"])
    as_of: date | None = Field(None, description="Evidence freeze date: filings after it are invisible. Default today.")
    decision: str = Field("", max_length=MAX_DECISION_CHARS,
                          examples=["Before we proceed with a deposit partnership with this bank, identify the "
                                    "governance risks and evidence gaps we should investigate."])
    private: bool = Field(False, description="Run every AI step on local models only (Ollama). No text leaves the machine.")


class CrashTestStarted(BaseModel):
    id: str
    status: str
    cached: bool
    worker_online: bool | None = None


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


def get_inline() -> bool:
    return get_settings().run_jobs_inline


def graph_runner(cik: str, as_of: date, decision: str, on_event: Callable[[list[dict]], None],
                 private: bool = False) -> dict:
    """Runs the LangGraph Crash-Test node by node and reports each node's events as it finishes."""
    from app.agents.graph import build_graph, default_services

    app = build_graph(default_services(), private=private)
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


def execute(job_id: str, cik: str, as_of: date, decision: str, store: Any, runner: Runner,
            private: bool = False) -> None:
    events: list[dict] = []

    def on_event(new: list[dict]) -> None:
        events.extend(new)
        store.update(job_id, status="running", events=events)

    try:
        store.update(job_id, status="running")
        try:
            state = runner(cik, as_of, decision, on_event, private)
        except TypeError:
            state = runner(cik, as_of, decision, on_event)
        if state.get("allowed") is False:
            reason = (state.get("guard_result") or {}).get("reason") or "input guard"
            store.update(job_id, status="blocked", events=events, error=f"Blocked by the input guard: {reason}")
        elif state.get("report"):
            mode = "hybrid + cross-encoder rerank" if get_settings().rerank_enabled else "hybrid (reranker disabled on this server)"
            report = {**state["report"], "retrieval_mode": mode}
            if private:
                s = get_settings()
                report["private"] = True
                report["private_models"] = [s.ollama_model_fast, s.ollama_model_general]
            store.update(job_id, status="done", events=events, report=report)
        else:
            store.update(job_id, status="failed", events=events, error="The Crash-Test produced no report.")
    except Exception as exc:  # last resort: a job must never stay "running" forever
        message = f"{type(exc).__name__}: {str(exc).strip().splitlines()[0] if str(exc).strip() else ''}"[:300]
        try:
            store.update(job_id, status="failed", events=events, error=message)
        except Exception:
            pass


def execute_claimed(job_id: str, cik: str, as_of: date, decision: str, store: Any, runner: Runner,
                    private: bool = False) -> None:
    """Inline mode: run only if this process wins the atomic claim (a worker may have taken the job first)."""
    try:
        if not store.claim(job_id):
            return
    except DatabaseError:
        return
    execute(job_id, cik, as_of, decision, store, runner, private=private)


def _worker(store: Any) -> dict | None:
    try:
        return store.worker_online()
    except DatabaseError:
        return None


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
                     store: Any = Depends(get_store), runner: Runner = Depends(get_runner),
                     inline: bool = Depends(get_inline), user: dict | None = Depends(get_optional_user),
                     users: Any = Depends(get_user_store)) -> CrashTestStarted:
    cik = normalize_cik(req.cik)
    as_of = req.as_of or date.today()
    if as_of > date.today():
        raise HTTPException(422, "as_of cannot be in the future.")
    if req.private and not check_private_available():
        raise HTTPException(409, PRIVATE_UNAVAILABLE)
    decision, key = decision_key(req.decision)
    try:
        cached = store.find_done(cik, as_of, key)
        if cached:
            response.status_code = 200
            return CrashTestStarted(id=cached["id"], status="done", cached=True)
        if user is None:
            raise HTTPException(401, "Log in, or use the demo account, to run a new Crash-Test. "
                                     "Precomputed demos open without an account.")
        limit = monthly_limit(user["role"], user["plan"])
        if limit is not None and users.usage_this_month(user["id"]) >= limit:
            raise HTTPException(403, f"Your {plan(user['plan'])['name']} plan includes {limit} Crash-Tests per month "
                                     f"and they are used. Upgrade or request a pilot on the Pricing page.")
        if store.busy():
            raise HTTPException(429, "Another live Crash-Test is running. Try again in a minute, or open a precomputed demo.")
        try:
            job_id = store.create(cik, as_of, decision, key, user_id=user["id"], private=req.private)
        except TypeError:
            job_id = store.create(cik, as_of, decision, key, user_id=user["id"])
    except DatabaseError as exc:
        raise HTTPException(503, f"Database unavailable: {exc}") from exc
    if inline:
        background.add_task(execute_claimed, job_id, cik, as_of, decision, store, runner, req.private)
        return CrashTestStarted(id=job_id, status="queued", cached=False)
    return CrashTestStarted(id=job_id, status="queued", cached=False, worker_online=_worker(store) is not None)


@router.get("/crash-tests/{job_id}", tags=["crash-tests"],
            summary="Poll a Crash-Test: status, live node events, report when done")
def get_crash_test(job_id: str, store: Any = Depends(get_store), inline: bool = Depends(get_inline)) -> dict:
    row = _row(store, job_id)
    now = datetime.now(timezone.utc)
    if not inline and row["status"] == "queued" and now - row["created_at"] > QUEUE_TIMEOUT:
        row["status"], row["error"] = "failed", NO_WORKER
        store.update(job_id, status="failed", error=NO_WORKER)
    elif row["status"] in ("queued", "running") and now - row["updated_at"] > STALE_AFTER:
        row["status"], row["error"] = "failed", "Timed out: no progress for 15 minutes."
        store.update(job_id, status="failed", error=row["error"])
    if row["status"] == "queued" and not inline:
        row["worker_online"] = _worker(store) is not None
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
        return {"cached": True, "memo": row["memo"], "markdown": to_markdown(row["memo"]), "markdown_bn": row["memo"].get("markdown_bn")}
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
    return {"cached": True, "memo": row["memo"], "markdown": to_markdown(row["memo"]), "markdown_bn": row["memo"].get("markdown_bn")}


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


@router.get("/status", tags=["status"], summary="Live mode and analysis worker status")
def status(store: Any = Depends(get_store), inline: bool = Depends(get_inline)) -> dict:
    if inline:
        return {"live_mode": "inline", "worker_online": True, "worker": None,
                "rerank_enabled": get_settings().rerank_enabled}
    worker = _worker(store)
    return {"live_mode": "worker", "worker_online": worker is not None,
            "worker": {"last_seen": worker["last_seen"], "busy": bool(worker["current_job"])} if worker else None,
            "rerank_enabled": worker["rerank_enabled"] if worker else None}


# ---------- Private Mode status ----------

def check_private_available() -> bool:
    """Probe Ollama /api/tags with a short timeout. Returns True when the runtime has the configured models."""
    s = get_settings()
    try:
        resp = httpx.get(f"{s.ollama_url}/api/tags", timeout=2.0)
        if resp.status_code != 200:
            return False
        models = resp.json().get("models", [])
        names = {m.get("name", "") for m in models} | {m.get("model", "") for m in models}
        fast_ok = any(s.ollama_model_fast in n for n in names)
        gen_ok = any(s.ollama_model_general in n for n in names)
        return fast_ok and gen_ok
    except Exception:
        return False


@router.get("/private/status", tags=["private mode"], summary="Whether Private Mode (local Ollama) is available")
def private_status() -> dict:
    s = get_settings()
    try:
        resp = httpx.get(f"{s.ollama_url}/api/tags", timeout=2.0)
        if resp.status_code != 200:
            return {"available": False, "models": [], "runtime": "ollama"}
        models = resp.json().get("models", [])
        names = {m.get("name", "") for m in models} | {m.get("model", "") for m in models}
        found = [n for n in names if any(req in n for req in (s.ollama_model_fast, s.ollama_model_general)) if n]
        fast_ok = any(s.ollama_model_fast in n for n in names)
        gen_ok = any(s.ollama_model_general in n for n in names)
        return {"available": fast_ok and gen_ok, "models": sorted(found), "runtime": "ollama"}
    except Exception:
        return {"available": False, "models": [], "runtime": "ollama"}

@router.get("/crash-tests", tags=["crash-tests"], summary="My Crash-Tests (private to the account)")
def my_crash_tests(user: dict = Depends(get_current_user), store: Any = Depends(get_store)) -> list[dict]:
    try:
        return store.list_for_user(user["id"])
    except DatabaseError as exc:
        raise HTTPException(503, f"Database unavailable: {exc}") from exc



BN_MEMO_SYSTEM = (
    "You translate a corporate-governance legal memo from English into formal, clear Bengali (Bangla script). "
    "Keep EXACTLY unchanged: the Markdown structure (#, ##, ###, -, *, **), finding ids in square brackets such as [REL-3], "
    "rule names such as 'Reg S-K Item 404(a)', form names (10-K, DEF 14A, PRE 14A, 8-K), company and person names, "
    "URLs, page numbers, and every passage inside double quotes (quoted evidence stays in the original English). "
    "In risk headings translate only the severity word: high -> উচ্চ, medium -> মাঝারি, low -> নিম্ন. "
    "Return only the translated Markdown, nothing else."
)


def get_memo_translator() -> Callable[[str], str]:
    from app.llm.client import get_llm

    llm = get_llm()

    def translate(markdown: str) -> str:
        r = llm.complete("bangla", [{"role": "system", "content": BN_MEMO_SYSTEM},
                                    {"role": "user", "content": markdown}], max_tokens=7000, max_wait=90)
        return r.text
    return translate


@router.post("/crash-tests/{job_id}/memo/bn", tags=["legal memo"],
             summary="Bengali translation of the legal memo (translated once, then cached)")
def translate_memo(job_id: str, store: Any = Depends(get_store),
                   translate: Callable[[str], str] = Depends(get_memo_translator)) -> dict:
    row = _row(store, job_id)
    memo = row.get("memo")
    if not memo:
        raise HTTPException(404, "No memo yet. Draft the English memo first.")
    if memo.get("markdown_bn"):
        return {"cached": True, "markdown": memo["markdown_bn"]}
    try:
        text = translate(to_markdown(memo)).strip()
    except Exception:
        raise HTTPException(503, "The translation model is unavailable right now. Please try again in a minute.")
    text = re.sub(r"^```(?:markdown|md)?\s*|\s*```$", "", text)
    if len(text) < 200:
        raise HTTPException(503, "The translation came back incomplete. Please try again.")
    store.update(job_id, memo={**memo, "markdown_bn": text})
    return {"cached": False, "markdown": text}
