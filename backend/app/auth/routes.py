"""Accounts and plans API.

GET  /api/plans               plans and add-ons from the business model (no live payments)
GET  /api/auth/questions      security questions to choose from
POST /api/auth/signup         create an account (18+ by date of birth; strong password; security question)
POST /api/auth/login          email + password (5 failures -> locked for 15 minutes)
POST /api/auth/forgot         the account's security question (a stable decoy for unknown emails)
POST /api/auth/reset          answer + new password (5 wrong answers -> locked for 15 minutes)
POST /api/auth/demo           one-click demo account: every feature, no limits
GET  /api/auth/me             the user and this month's Crash-Test usage
POST /api/plans/request       record an upgrade or pilot request (no payment taken)
"""

from __future__ import annotations

import math
import re
import secrets
from datetime import date, datetime, timedelta, timezone
from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.auth.deps import get_current_user, get_user_store, public_user, session, usage
from app.auth.security import (
    SECURITY_QUESTIONS, check_birth_date, decoy_question, hash_secret, normalize_answer, password_problems,
    verify_secret,
)
from app.business.plans import ADD_ONS, PLAN_IDS, PLANS
from app.db import DatabaseError

router = APIRouter(prefix="/api")

MAX_FAILURES = 5
LOCK_MINUTES = 15
DEMO_EMAIL = "demo@nirikkha.demo"
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
WRONG_LOGIN = "Email or password is incorrect."
WRONG_ANSWER = "The answer is not correct."
_DUMMY_HASH = hash_secret("timing-equaliser-not-a-password")


class SignupRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    email: str = Field(..., max_length=254)
    password: str = Field(..., max_length=200)
    date_of_birth: date
    security_question: str
    security_answer: str = Field(..., min_length=2, max_length=100)
    organization: str | None = Field(None, max_length=120)
    job_role: str | None = Field(None, max_length=80)


class LoginRequest(BaseModel):
    email: str = Field(..., max_length=254)
    password: str = Field(..., max_length=200)


class ForgotRequest(BaseModel):
    email: str = Field(..., max_length=254)


class ResetRequest(BaseModel):
    email: str = Field(..., max_length=254)
    answer: str = Field(..., max_length=100)
    new_password: str = Field(..., max_length=200)


class PlanRequest(BaseModel):
    plan: str
    kind: Literal["upgrade", "pilot"] = "upgrade"
    note: str | None = Field(None, max_length=500)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _db(fn, *args, **kwargs):
    try:
        return fn(*args, **kwargs)
    except DatabaseError as exc:
        raise HTTPException(503, f"Database unavailable: {exc}") from exc


def _email(raw: str) -> str:
    return raw.strip().lower()


def _locked_minutes(until: datetime | None) -> int | None:
    if until and until > _now():
        return max(1, math.ceil((until - _now()).total_seconds() / 60))
    return None


def _fail(users: Any, user: dict, prefix: str) -> None:
    failures = (user.get(f"{prefix}_failures") or 0) + 1
    if failures >= MAX_FAILURES:
        _db(users.update, user["id"], **{f"{prefix}_failures": 0,
                                         f"{prefix}_locked_until": _now() + timedelta(minutes=LOCK_MINUTES)})
    else:
        _db(users.update, user["id"], **{f"{prefix}_failures": failures})


@router.get("/plans", tags=["plans"], summary="Plans and add-ons (proposed list prices, USD)")
def list_plans() -> dict:
    return {"currency": "USD", "plans": PLANS, "add_ons": ADD_ONS,
            "note": "Proposed list prices, to be finalised with pilot customers. No live payments in the prototype."}


@router.get("/auth/questions", tags=["auth"], summary="Security questions to choose from")
def questions() -> list[str]:
    return SECURITY_QUESTIONS


@router.post("/auth/signup", status_code=201, tags=["auth"], summary="Create an account")
def signup(req: SignupRequest, users: Any = Depends(get_user_store)) -> dict:
    email = _email(req.email)
    if not EMAIL_RE.match(email):
        raise HTTPException(422, "Please enter a valid email address.")
    problem = check_birth_date(req.date_of_birth)
    if problem:
        raise HTTPException(422, problem)
    problems = password_problems(req.password)
    if problems:
        raise HTTPException(422, "Password needs: " + "; ".join(problems) + ".")
    if req.security_question not in SECURITY_QUESTIONS:
        raise HTTPException(422, "Please choose one of the listed security questions.")
    answer = normalize_answer(req.security_answer)
    if len(answer) < 2:
        raise HTTPException(422, "Please give an answer to the security question.")
    if _db(users.get_by_email, email):
        raise HTTPException(409, "An account with this email already exists. Log in or reset the password.")
    user = _db(users.create, email=email, name=req.name.strip(),
               organization=(req.organization or "").strip() or None, job_role=(req.job_role or "").strip() or None,
               password_hash=hash_secret(req.password), security_question=req.security_question,
               security_answer_hash=hash_secret(answer), role="user", plan="free", adult_verified=True)
    return session(user)


@router.post("/auth/login", tags=["auth"], summary="Log in with email and password")
def login(req: LoginRequest, users: Any = Depends(get_user_store)) -> dict:
    user = _db(users.get_by_email, _email(req.email))
    if user is None or user["role"] == "demo":
        verify_secret(_DUMMY_HASH, req.password)   # same work as a real check: no timing hint
        raise HTTPException(401, WRONG_LOGIN)
    minutes = _locked_minutes(user.get("login_locked_until"))
    if minutes:
        raise HTTPException(429, f"Too many failed attempts. Try again in {minutes} minute(s).")
    if not verify_secret(user["password_hash"], req.password):
        _fail(users, user, "login")
        raise HTTPException(401, WRONG_LOGIN)
    _db(users.update, user["id"], login_failures=0, login_locked_until=None, last_login_at=_now())
    return session(user)


@router.post("/auth/forgot", tags=["auth"], summary="Get the security question for an email")
def forgot(req: ForgotRequest, users: Any = Depends(get_user_store)) -> dict:
    email = _email(req.email)
    user = _db(users.get_by_email, email)
    question = user["security_question"] if user and user["role"] != "demo" else decoy_question(email)
    return {"question": question}


@router.post("/auth/reset", tags=["auth"], summary="Answer the security question and set a new password")
def reset(req: ResetRequest, users: Any = Depends(get_user_store)) -> dict:
    problems = password_problems(req.new_password)
    if problems:
        raise HTTPException(422, "Password needs: " + "; ".join(problems) + ".")
    user = _db(users.get_by_email, _email(req.email))
    if user is None or user["role"] == "demo":
        verify_secret(_DUMMY_HASH, req.answer)
        raise HTTPException(401, WRONG_ANSWER)
    minutes = _locked_minutes(user.get("reset_locked_until"))
    if minutes:
        raise HTTPException(429, f"Too many wrong answers. Try again in {minutes} minute(s).")
    if not verify_secret(user["security_answer_hash"], normalize_answer(req.answer)):
        _fail(users, user, "reset")
        raise HTTPException(401, WRONG_ANSWER)
    _db(users.update, user["id"], password_hash=hash_secret(req.new_password), reset_failures=0,
        reset_locked_until=None, login_failures=0, login_locked_until=None, last_login_at=_now())
    return session(user)


@router.post("/auth/demo", tags=["auth"], summary="One-click demo account (every feature, no limits)")
def demo(users: Any = Depends(get_user_store)) -> dict:
    user = _db(users.get_by_email, DEMO_EMAIL)
    if user is None:
        user = _db(users.create, email=DEMO_EMAIL, name="Demo reviewer", organization="Nirikkha demo",
                   job_role="Judge / reviewer", password_hash=hash_secret(secrets.token_urlsafe(32)),
                   security_question=SECURITY_QUESTIONS[0], security_answer_hash=hash_secret(secrets.token_urlsafe(16)),
                   role="demo", plan="free", adult_verified=True)
    return session(user)


@router.get("/auth/me", tags=["auth"], summary="The logged-in user and this month's usage")
def me(user: dict = Depends(get_current_user), users: Any = Depends(get_user_store)) -> dict:
    return {"user": public_user(user), "usage": _db(usage, users, user)}


@router.post("/plans/request", status_code=201, tags=["plans"], summary="Request an upgrade or a pilot (no payment)")
def request_plan(req: PlanRequest, user: dict = Depends(get_current_user), users: Any = Depends(get_user_store)) -> dict:
    if req.plan not in PLAN_IDS:
        raise HTTPException(422, "Unknown plan.")
    request_id = _db(users.create_plan_request, user["id"], req.plan, req.kind, (req.note or "").strip() or None)
    return {"id": request_id, "status": "open",
            "message": "Thanks, your request is recorded. No payment is taken in the prototype; we will contact you."}