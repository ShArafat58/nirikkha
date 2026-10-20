"""FastAPI dependencies: the user store and the logged-in user from the Authorization: Bearer token."""

from __future__ import annotations

from functools import lru_cache
from typing import Any

from fastapi import Depends, Header, HTTPException

from app.auth.security import auth_secret, create_token, read_token
from app.business.plans import monthly_limit
from app.config import get_settings
from app.db import DatabaseError

PUBLIC_FIELDS = ("id", "email", "name", "organization", "job_role", "role", "plan", "created_at")


@lru_cache
def get_user_store():
    from app.auth.store import PostgresUserStore
    return PostgresUserStore()


def secret() -> str:
    s = get_settings()
    return auth_secret(s.auth_secret, s.app_env)


def get_optional_user(authorization: str | None = Header(None), users: Any = Depends(get_user_store)) -> dict | None:
    if not authorization or not authorization.lower().startswith("bearer "):
        return None
    claims = read_token(authorization[7:].strip(), secret())
    if not claims:
        raise HTTPException(401, "Your session has expired. Please log in again.")
    try:
        user = users.get(claims["sub"])
    except DatabaseError as exc:
        raise HTTPException(503, f"Database unavailable: {exc}") from exc
    if not user:
        raise HTTPException(401, "Your session has expired. Please log in again.")
    return user


def get_current_user(user: dict | None = Depends(get_optional_user)) -> dict:
    if user is None:
        raise HTTPException(401, "Please log in.")
    return user


def public_user(user: dict) -> dict:
    return {k: user.get(k) for k in PUBLIC_FIELDS}


def session(user: dict) -> dict:
    return {"token": create_token(user["id"], user["role"], secret()), "user": public_user(user)}


def usage(users: Any, user: dict) -> dict:
    limit = monthly_limit(user["role"], user["plan"])
    used = users.usage_this_month(user["id"])
    return {"used_this_month": used, "limit": limit, "unlimited": limit is None,
            "remaining": None if limit is None else max(0, limit - used)}