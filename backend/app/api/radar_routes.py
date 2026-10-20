"""Regulatory Change Radar API.

Reading alerts is public (they come from public filings and public rules). Approve / Reject
needs a signed-in user and is recorded in an audit trail. A scan can be triggered by a
scheduler (n8n) with the RADAR_SCAN_TOKEN shared secret.
"""
from __future__ import annotations

import hmac
import os
from typing import Any, Literal

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, Field

from app.auth.deps import get_current_user
from app.radar.store import PostgresRadarStore, RadarStore

router = APIRouter(prefix="/api/radar", tags=["radar"])


def get_radar_store() -> RadarStore:
    return PostgresRadarStore()


class DecisionIn(BaseModel):
    decision: Literal["approve", "reject"]
    note: str | None = Field(default=None, max_length=500)


def _who(user: Any) -> tuple[str | None, str | None]:
    if isinstance(user, dict):
        return (str(user.get("id")) if user.get("id") else None), user.get("email")
    return (str(getattr(user, "id", "")) or None), getattr(user, "email", None)


def _summary(alerts: list[dict]) -> dict:
    out: dict = {"total": len(alerts), "pending": 0, "approved": 0, "rejected": 0,
                 "by_priority": {"high": 0, "medium": 0, "low": 0}, "by_stream": {}}
    for a in alerts:
        out[a["status"]] = out.get(a["status"], 0) + 1
        out["by_priority"][a["priority"]] += 1
        out["by_stream"][a["stream"]] = out["by_stream"].get(a["stream"], 0) + 1
    return out


@router.get("")
def list_alerts(cik: str | None = None, store: RadarStore = Depends(get_radar_store)) -> dict:
    try:
        alerts = store.list(cik)
    except Exception:
        raise HTTPException(status_code=503, detail="The Radar is temporarily unavailable. Please try again.")
    return {
        "summary": _summary(alerts),
        "alerts": alerts,
        "streams": [
            {"id": "regulatory", "title": "SEC rule changes (curated)"},
            {"id": "filing", "title": "New filings on SEC EDGAR"},
        ],
        "note": "Priority is rule-based. No follow-up action counts as started until a person approves it.",
    }


@router.post("/alerts/{alert_id}/decision")
def decide(alert_id: str, body: DecisionIn, user: Any = Depends(get_current_user),
           store: RadarStore = Depends(get_radar_store)) -> dict:
    user_id, email = _who(user)
    note = (body.note or "").strip() or None
    try:
        alert = store.decide(alert_id, body.decision, note, user_id, email)
    except Exception:
        raise HTTPException(status_code=503, detail="Could not save the decision. Please try again.")
    if alert is None:
        raise HTTPException(status_code=404, detail="Alert not found.")
    return {"alert": alert, "history": store.history(alert_id)}


@router.get("/alerts/{alert_id}/history")
def history(alert_id: str, store: RadarStore = Depends(get_radar_store)) -> dict:
    try:
        if store.get(alert_id) is None:
            raise HTTPException(status_code=404, detail="Alert not found.")
        return {"history": store.history(alert_id)}
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=503, detail="The Radar is temporarily unavailable.")


@router.post("/scan")
def run_scan(x_radar_token: str | None = Header(default=None), store: RadarStore = Depends(get_radar_store)) -> dict:
    expected = os.getenv("RADAR_SCAN_TOKEN", "")
    if not expected:
        raise HTTPException(status_code=503, detail="Scheduled scans are not configured on this server.")
    if not x_radar_token or not hmac.compare_digest(x_radar_token, expected):
        raise HTTPException(status_code=401, detail="Invalid scan token.")
    from app.radar import engine

    try:
        alerts = engine.scan(use_edgar=True)
        saved = store.upsert(alerts)
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Scan failed: {type(exc).__name__}")
    return {"saved": saved, "summary": engine.summarise(alerts)}