"""Crash-Test run store in Supabase Postgres (table crash_tests, sql/003 and sql/004).

One short connection per call: fine for polling every few seconds on the free tier.
"""

from __future__ import annotations

import json
from datetime import date, datetime, timedelta, timezone
from typing import Any

from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

from app.db import connect

COLUMNS = ("id::text as id, cik, as_of, decision, decision_hash, status, events, report, memo, error, source, "
           "created_at, updated_at")
ACTIVE_WINDOW = timedelta(minutes=10)   # a queued/running job updated within this window blocks a new live run
UPDATABLE = {"status", "events", "report", "memo", "error", "source"}
JSON_FIELDS = {"events", "report", "memo"}
RUNS_PER_COMPANY = 5


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
            params.append(_jsonb(value) if key in JSON_FIELDS else value)
        sets.append("updated_at = now()")
        self._one(f"update crash_tests set {', '.join(sets)} where id = %s", (*params, job_id))

    def get(self, job_id: str) -> dict | None:
        return self._one(f"select {COLUMNS} from crash_tests where id = %s", (job_id,))

    def delete(self, job_id: str) -> None:
        self._one("delete from crash_tests where id = %s", (job_id,))

    def companies(self) -> list[dict]:
        """Companies with loaded filings, chunk counts and their latest finished Crash-Tests."""
        with connect(autocommit=True) as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute(
                    "select f.cik, max(f.company) as company, count(*)::int as filing_count, "
                    "json_agg(json_build_object('accession_no', f.accession_no, 'form', f.form, "
                    "'filing_date', f.filing_date, 'has_page_markers', f.has_page_markers, 'url', f.url) "
                    "order by f.filing_date) as filings "
                    "from filings f group by f.cik order by max(f.company)")
                companies = cur.fetchall()
                cur.execute("select f.cik, count(*)::int as n from chunks c join filings f using (accession_no) "
                            "group by f.cik")
                chunks = {r["cik"]: r["n"] for r in cur.fetchall()}
                cur.execute(
                    "select id::text as id, cik, as_of, decision, source, updated_at, memo is not null as has_memo, "
                    "(report->'health'->>'score')::int as score, report->'health'->>'band' as band, "
                    "(report->'health'->'coverage'->>'pct')::int as coverage_pct "
                    "from crash_tests where status = 'done' order by updated_at desc limit 100")
                runs = cur.fetchall()
        by_cik: dict[str, list[dict]] = {}
        for r in runs:
            by_cik.setdefault(r["cik"], []).append(r)
        for c in companies:
            c["chunk_count"] = chunks.get(c["cik"], 0)
            c["crash_tests"] = by_cik.get(c["cik"], [])[:RUNS_PER_COMPANY]
        return companies