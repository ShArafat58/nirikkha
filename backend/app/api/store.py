"""Crash-Test run store in Supabase Postgres (table crash_tests, sql/003_crash_tests.sql).

One short connection per call: fine for polling every few seconds on the free tier.
"""

from __future__ import annotations

import json
from datetime import date, datetime, timedelta, timezone
from typing import Any

from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

from app.db import connect

COLUMNS = "id::text as id, cik, as_of, decision, decision_hash, status, events, report, error, source, created_at, updated_at"
ACTIVE_WINDOW = timedelta(minutes=10)   # a queued/running job updated within this window blocks a new live run
UPDATABLE = {"status", "events", "report", "error", "source"}


def _jsonb(value: Any) -> Jsonb:
    return Jsonb(value, dumps=lambda o: json.dumps(o, default=str))


class PostgresStore:
    def _one(self, sql: str, params: tuple = ()) -> dict | None:
        with connect(autocommit=True) as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute(sql, params)
                return cur.fetchone() if cur.description else None

    def find_done(self, cik: str, as_of: date, decision_hash: str) -> dict | None:
        return self._one(f"select {COLUMNS} from crash_tests where cik = %s and as_of = %s and decision_hash = %s "
                         f"and status = 'done' order by updated_at desc limit 1", (cik, as_of, decision_hash))

    def busy(self) -> bool:
        since = datetime.now(timezone.utc) - ACTIVE_WINDOW
        row = self._one("select count(*) as n from crash_tests where status in ('queued', 'running') and updated_at > %s",
                        (since,))
        return bool(row and row["n"])

    def create(self, cik: str, as_of: date, decision: str, decision_hash: str, source: str = "live") -> str:
        row = self._one("insert into crash_tests (cik, as_of, decision, decision_hash, status, source) "
                        "values (%s, %s, %s, %s, 'queued', %s) returning id::text as id",
                        (cik, as_of, decision, decision_hash, source))
        return row["id"]

    def update(self, job_id: str, **fields: Any) -> None:
        bad = set(fields) - UPDATABLE
        if bad:
            raise ValueError(f"cannot update {sorted(bad)}")
        sets, params = [], []
        for key, value in fields.items():
            sets.append(f"{key} = %s")
            params.append(_jsonb(value) if key in ("events", "report") else value)
        sets.append("updated_at = now()")
        self._one(f"update crash_tests set {', '.join(sets)} where id = %s", (*params, job_id))

    def get(self, job_id: str) -> dict | None:
        return self._one(f"select {COLUMNS} from crash_tests where id = %s", (job_id,))

    def delete(self, job_id: str) -> None:
        self._one("delete from crash_tests where id = %s", (job_id,))