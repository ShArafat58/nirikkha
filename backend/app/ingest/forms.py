"""Look up a filing's form type (DEF 14A, PRE 14A, 10-K ...) by accession number.

Graph rows only carry the accession number, so citations built from them
read the form from the local parsed-filing cache. Falls back to a default
when the cache file is not present (tests, or a host without the cache).
"""
from __future__ import annotations

import json
import re
from functools import lru_cache

_FORM_RE = re.compile(r'"form"\s*:\s*"([^"]+)"')


@lru_cache(maxsize=128)
def form_of(accession_no: str, default: str = "DEF 14A") -> str:
    try:
        from app.config import get_settings

        path = get_settings().cache_dir / "parsed" / f"{accession_no}.json"
        if not path.exists():
            return default
        with path.open(encoding="utf-8") as f:
            head = f.read(4096)  # top-level fields come first in the parsed JSON
        match = _FORM_RE.search(head)
        if match:
            return match.group(1)
        return json.loads(path.read_text(encoding="utf-8")).get("form") or default
    except Exception:  # a lookup failure must never break report building
        return default