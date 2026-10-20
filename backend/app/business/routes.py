"""Demo checkout API: shows the full subscription flow without taking money.

POST /api/billing/checkout   choose a paid plan and a payment method -> simulated payment + plan activated
POST /api/billing/cancel     back to the Free plan
GET  /api/billing/history    the account's simulated subscriptions

No card number, account number, PIN or OTP is ever requested or stored. Live payments (international card gateway;
bKash / Nagad merchant account or SSLCommerz in Bangladesh) are on the roadmap.
"""

from __future__ import annotations

import secrets
from functools import lru_cache
from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.auth.deps import get_current_user
from app.business.plans import PLAN_IDS, plan
from app.db import DatabaseError

router = APIRouter(prefix="/api/billing", tags=["billing (demo)"])

DEMO_NOTE = ("Demo checkout: no money was charged and no card, account or PIN details were collected. "
             "Live payments (international card gateway; bKash / Nagad merchant account or SSLCommerz in Bangladesh) "
             "are on the roadmap.")


@lru_cache
def get_billing_store():
    from app.business.store import PostgresBillingStore
    return PostgresBillingStore()


class Checkout(BaseModel):
    plan: str
    method: Literal["mobile_banking", "card", "bank_transfer"]


def _reference() -> str:
    return f"SIM-{secrets.token_hex(4).upper()}"


def _db(fn, *args):
    try:
        return fn(*args)
    except DatabaseError as exc:
        raise HTTPException(503, f"Database unavailable: {exc}") from exc


@router.post("/checkout", status_code=201, summary="Demo checkout: activate a paid plan without taking money")
def checkout(body: Checkout, user: dict = Depends(get_current_user), store: Any = Depends(get_billing_store)) -> dict:
    if body.plan not in PLAN_IDS:
        raise HTTPException(422, "Unknown plan.")
    p = plan(body.plan)
    if p["price_usd"] is None:
        raise HTTPException(422, "Enterprise is an annual contract. Please request a pilot.")
    if p["price_usd"] == 0:
        raise HTTPException(422, "The Free plan needs no payment.")
    if body.plan == user.get("plan"):
        raise HTTPException(409, "You are already on this plan.")
    record = _db(store.subscribe, user["id"], body.plan, body.method, float(p["price_usd"]), _reference())
    return {**record, "plan_name": p["name"], "simulated": True, "note": DEMO_NOTE}


@router.post("/cancel", summary="Return to the Free plan")
def cancel(user: dict = Depends(get_current_user), store: Any = Depends(get_billing_store)) -> dict:
    if user.get("plan") == "free":
        raise HTTPException(409, "You are already on the Free plan.")
    record = _db(store.subscribe, user["id"], "free", "none", 0.0, _reference())
    return {**record, "plan_name": "Free", "simulated": True, "note": DEMO_NOTE}


@router.get("/history", summary="The account's simulated subscriptions")
def history(user: dict = Depends(get_current_user), store: Any = Depends(get_billing_store)) -> list[dict]:
    return _db(store.history, user["id"])