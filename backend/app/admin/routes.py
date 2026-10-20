"""Admin API (role admin only).

GET  /api/admin/overview              accounts by plan, projected revenue (labelled), usage, model tokens, unit economics
GET  /api/admin/users                 accounts with this month's usage
POST /api/admin/users/{id}/plan       set a plan (e.g. after a pilot is agreed; no payment in the prototype)
GET  /api/admin/plan-requests         upgrade / pilot requests
POST /api/admin/plan-requests/{id}    set request status
GET  /api/admin/jobs                  recent Crash-Tests
GET  /api/admin/reviews               human review queue (Sentinel-flagged findings, latest decision)
POST /api/admin/reviews               approve / reject a flagged finding with a note (kept as an audit trail)
"""

from __future__ import annotations

from functools import lru_cache
from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.auth.deps import get_current_user
from app.business.plans import PLAN_IDS, PLANS, projected_mrr
from app.db import DatabaseError

router = APIRouter(prefix="/api/admin", tags=["admin"])


@lru_cache
def get_admin_store():
    from app.admin.store import PostgresAdminStore
    return PostgresAdminStore()


def require_admin(user: dict = Depends(get_current_user)) -> dict:
    if user.get("role") != "admin":
        raise HTTPException(403, "Admin access only.")
    return user


def _db(fn, *args):
    try:
        return fn(*args)
    except DatabaseError as exc:
        raise HTTPException(503, f"Database unavailable: {exc}") from exc


class PlanChange(BaseModel):
    plan: str


class RequestStatus(BaseModel):
    status: Literal["open", "contacted", "closed"]


class Review(BaseModel):
    crash_test_id: str
    finding_id: str = Field(..., max_length=20)
    decision: Literal["approve", "reject"]
    note: str | None = Field(None, max_length=1000)


def unit_economics(per_test: dict | None) -> dict:
    per_test = per_test or {}
    revenue = [{"plan": p["id"], "revenue_per_crash_test_usd": round(p["price_usd"] / p["crash_tests_per_month"], 2)}
               for p in PLANS if p["price_usd"] and p["crash_tests_per_month"]]
    return {
        "measured": {"crash_tests": per_test.get("n", 0), "avg_tokens": per_test.get("avg_tokens"),
                     "avg_llm_calls": float(per_test["avg_llm_calls"]) if per_test.get("avg_llm_calls") is not None else None,
                     "avg_seconds": per_test.get("avg_seconds"), "infra_cost_usd_total": per_test.get("cost_usd", 0.0)},
        "revenue_per_crash_test": revenue,
        "note": ("Measured tokens and time come from real runs. Current infrastructure runs on free tiers ($0). "
                 "A paid-tier cost estimate needs current provider prices, which are not set in this prototype."),
    }


@router.get("/overview", summary="Business and operations overview")
def overview(_: dict = Depends(require_admin), store: Any = Depends(get_admin_store)) -> dict:
    data = _db(store.overview)
    users_by_plan: dict[str, int] = {}
    for row in data["accounts"]:
        if row["role"] == "user":
            users_by_plan[row["plan"]] = users_by_plan.get(row["plan"], 0) + row["n"]
    return {**data, "users_by_plan": users_by_plan, "projected_revenue": projected_mrr(users_by_plan),
            "unit_economics": unit_economics(data.get("per_crash_test"))}


@router.get("/users", summary="Accounts with this month's usage")
def users(_: dict = Depends(require_admin), store: Any = Depends(get_admin_store)) -> list[dict]:
    return _db(store.users)


@router.post("/users/{user_id}/plan", summary="Set an account's plan")
def set_plan(user_id: str, body: PlanChange, _: dict = Depends(require_admin),
             store: Any = Depends(get_admin_store)) -> dict:
    if body.plan not in PLAN_IDS:
        raise HTTPException(422, "Unknown plan.")
    if not _db(store.set_plan, user_id, body.plan):
        raise HTTPException(404, "User not found.")
    return {"id": user_id, "plan": body.plan}


@router.get("/plan-requests", summary="Upgrade and pilot requests")
def plan_requests(_: dict = Depends(require_admin), store: Any = Depends(get_admin_store)) -> list[dict]:
    return _db(store.plan_requests)


@router.post("/plan-requests/{request_id}", summary="Set a request's status")
def set_request_status(request_id: str, body: RequestStatus, _: dict = Depends(require_admin),
                       store: Any = Depends(get_admin_store)) -> dict:
    if not _db(store.set_request_status, request_id, body.status):
        raise HTTPException(404, "Request not found.")
    return {"id": request_id, "status": body.status}


@router.get("/jobs", summary="Recent Crash-Tests")
def jobs(_: dict = Depends(require_admin), store: Any = Depends(get_admin_store)) -> list[dict]:
    return _db(store.jobs)


@router.get("/reviews", summary="Human review queue")
def reviews(_: dict = Depends(require_admin), store: Any = Depends(get_admin_store)) -> list[dict]:
    return _db(store.review_queue)


@router.post("/reviews", status_code=201, summary="Approve or reject a flagged finding")
def add_review(body: Review, admin: dict = Depends(require_admin), store: Any = Depends(get_admin_store)) -> dict:
    review_id = _db(store.add_review, body.crash_test_id, body.finding_id, body.decision,
                    (body.note or "").strip() or None, admin["id"])
    if review_id is None:
        raise HTTPException(404, "Finding not found in that Crash-Test.")
    return {"id": review_id, "decision": body.decision}