"""Company sector from SEC EDGAR (SIC code), cached locally.

Used to decide whether financial-sector best practices (such as a designated
Chief Risk Officer) apply. Unknown sector -> the rule still applies.
"""
from __future__ import annotations

import json
import os
from functools import lru_cache

FINANCE_SIC = range(6000, 6800)  # SEC Division H: finance, insurance and real estate


@lru_cache(maxsize=256)
def sic_code(cik: str) -> int | None:
    from app.config import get_settings
    from app.ingest.edgar import normalize_cik

    cik = normalize_cik(cik)
    settings = get_settings()
    path = settings.cache_dir / "sic.json"
    try:
        cache = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    except (OSError, json.JSONDecodeError):
        cache = {}
    if cik in cache:
        return cache[cik]
    if os.getenv("PYTEST_CURRENT_TEST"):
        return None  # tests never call EDGAR
    try:
        from app.ingest.edgar import EdgarClient

        with EdgarClient(settings.sec_user_agent, cache_dir=settings.cache_dir) as client:
            data = client._get_json(f"https://data.sec.gov/submissions/CIK{cik}.json")
        raw = str(data.get("sic") or "")
        code = int(raw) if raw.isdigit() else None
    except Exception:
        return None
    cache[cik] = code
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(cache), encoding="utf-8")
    except OSError:
        pass
    return code


def is_financial(cik: str) -> bool | None:
    code = sic_code(cik)
    return None if code is None else code in FINANCE_SIC