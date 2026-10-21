"""Shared helpers for the Nirikkha MCP servers: config, HTTP to the Nirikkha API, transport choice."""
from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any

import httpx

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent


def _load_env() -> None:
    env = HERE / ".env"
    if env.exists():
        for line in env.read_text(encoding="utf-8").splitlines():
            if "=" in line and not line.lstrip().startswith("#"):
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())


_load_env()
API = os.getenv("NIRIKKHA_API_URL", "http://localhost:8000").rstrip("/")
UA = os.getenv("SEC_USER_AGENT", "Nirikkha MCP (set SEC_USER_AGENT)")


def api(method: str, path: str, token: str | None = None, **kw: Any) -> Any:
    """Call the Nirikkha API and return JSON, or a dict with an 'error' the model can read."""
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    try:
        r = httpx.request(method, f"{API}{path}", headers=headers, timeout=90, **kw)
    except httpx.HTTPError as exc:
        return {"error": f"Nirikkha API unreachable at {API}: {type(exc).__name__}"}
    if r.status_code >= 400:
        try:
            detail = r.json().get("detail")
        except Exception:
            detail = r.text[:200]
        return {"error": f"HTTP {r.status_code}: {detail}"}
    return r.json()


def run(server) -> None:
    """stdio by default (Claude Desktop, Antigravity); --http for Streamable HTTP."""
    if "--http" in sys.argv:
        server.run(transport="streamable-http")
    else:
        server.run()