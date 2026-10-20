"""Accounts and plan requests in Supabase Postgres (sql/006_auth.sql)."""

from __future__ import annotations

from typing import Any

from psycopg.rows import dict_row

from app.db import connect

USER_COLUMNS = ("id::text as id, email, name, organization, job_role, password_hash, security_question, "
                "security_answer_hash, role, plan, adult_verified, login_failures, login_locked_until, "
                "reset_failures, reset_locked_until, created_at, last_login_at")
CREATE_FIELDS = ("email", "name", "organization", "job_role", "password_hash", "security_question",
                 "security_answer_hash", "role", "plan", "adult_verified")
UPDATABLE = {"name", "organization", "job_role", "password_hash", "security_question", "security_answer_hash",
             "role", "plan", "login_failures", "login_locked_until", "reset_failures", "reset_locked_until",
             "last_login_at"}


class PostgresUserStore:
    def _one(self, sql: str, params: tuple = ()) -> dict | None:
        with connect(autocommit=True) as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute(sql, params)
                return cur.fetchone() if cur.description else None

    def get_by_email(self, email: str) -> dict | None:
        return self._one(f"select {USER_COLUMNS} from users where email = %s", (email,))

    def get(self, user_id: str) -> dict | None:
        return self._one(f"select {USER_COLUMNS} from users where id::text = %s", (user_id,))

    def create(self, **fields: Any) -> dict:
        values = [fields.get(k) for k in CREATE_FIELDS]
        return self._one(f"insert into users ({', '.join(CREATE_FIELDS)}) values ({', '.join(['%s'] * len(CREATE_FIELDS))}) "
                         f"returning {USER_COLUMNS}", tuple(values))

    def update(self, user_id: str, **fields: Any) -> None:
        bad = set(fields) - UPDATABLE
        if bad:
            raise ValueError(f"cannot update {sorted(bad)}")
        sets = ", ".join(f"{k} = %s" for k in fields)
        self._one(f"update users set {sets} where id::text = %s", (*fields.values(), user_id))

    def usage_this_month(self, user_id: str) -> int:
        row = self._one("select count(*)::int as n from crash_tests where user_id::text = %s "
                        "and created_at >= date_trunc('month', now()) and status <> 'failed'", (user_id,))
        return row["n"] if row else 0

    def create_plan_request(self, user_id: str, plan: str, kind: str, note: str | None) -> str:
        row = self._one("insert into plan_requests (user_id, plan, kind, note) values (%s, %s, %s, %s) "
                        "returning id::text as id", (user_id, plan, kind, note))
        return row["id"]