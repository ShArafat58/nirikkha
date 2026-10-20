"""Admin queries: accounts, plan requests, jobs, model usage, human review queue (sql/006, sql/007)."""

from __future__ import annotations

from typing import Any

from psycopg.rows import dict_row

from app.db import connect

REVIEW_QUEUE_SQL = """
select t.id::text as crash_test_id, t.report->>'company' as company, t.as_of, t.decision,
       f->>'id' as finding_id, f->>'title' as title, f->>'risk_severity' as severity,
       f->>'evidence_confidence' as confidence, f->'sentinel'->>'verdict' as verdict,
       r.decision as review, r.note as review_note, r.created_at as reviewed_at, ru.email as reviewer
from crash_tests t
cross join jsonb_array_elements(t.report->'findings') f
left join lateral (select * from finding_reviews r where r.crash_test_id = t.id and r.finding_id = f->>'id'
                   order by r.created_at desc limit 1) r on true
left join users ru on ru.id = r.reviewer_id
where t.status = 'done' and coalesce((f->'sentinel'->>'human_review')::boolean, false)
order by (r.decision is not null), t.updated_at desc
limit 200
"""


class PostgresAdminStore:
    def _all(self, sql: str, params: tuple = ()) -> list[dict]:
        with connect(autocommit=True) as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute(sql, params)
                return cur.fetchall() if cur.description else []

    def _one(self, sql: str, params: tuple = ()) -> dict | None:
        rows = self._all(sql, params)
        return rows[0] if rows else None

    def overview(self) -> dict:
        return {
            "accounts": self._all("select role, plan, count(*)::int as n from users group by role, plan"),
            "signups": self._one("select count(*)::int as users, count(*) filter (where created_at > now() - interval '30 days')::int "
                                 "as last_30_days from users where role = 'user'"),
            "crash_tests_by_status": self._all("select status, count(*)::int as n from crash_tests group by status"),
            "crash_tests_this_month": self._one("select count(*)::int as n from crash_tests "
                                                "where created_at >= date_trunc('month', now())")["n"],
            "open_plan_requests": self._one("select count(*)::int as n from plan_requests where status = 'open'")["n"],
            "model_usage": self._all(
                "select c->>'model' as model, c->>'node' as node, count(*)::int as calls, "
                "sum((c->>'input_tokens')::int)::int as input_tokens, sum((c->>'output_tokens')::int)::int as output_tokens, "
                "avg((c->>'latency_ms')::numeric)::int as avg_latency_ms "
                "from crash_tests t, jsonb_array_elements(t.report->'usage'->'calls') c "
                "where t.status = 'done' group by 1, 2 order by calls desc"),
            "per_crash_test": self._one(
                "select count(*)::int as n, "
                "avg((report->'usage'->>'input_tokens')::numeric + (report->'usage'->>'output_tokens')::numeric)::int as avg_tokens, "
                "avg((report->'usage'->>'llm_calls')::numeric)::numeric(6,1) as avg_llm_calls, "
                "avg(extract(epoch from (updated_at - created_at)))::int as avg_seconds, "
                "coalesce(sum((report->'usage'->>'cost_usd')::numeric), 0)::float as cost_usd "
                "from crash_tests where status = 'done'"),
        }

    def users(self) -> list[dict]:
        return self._all(
            "select u.id::text as id, u.email, u.name, u.organization, u.job_role, u.role, u.plan, u.created_at, "
            "u.last_login_at, (select count(*)::int from crash_tests t where t.user_id = u.id "
            "and t.created_at >= date_trunc('month', now()) and t.status <> 'failed') as used_this_month "
            "from users u order by u.created_at desc limit 200")

    def set_plan(self, user_id: str, plan: str) -> bool:
        return self._one("update users set plan = %s where id::text = %s returning id", (plan, user_id)) is not None

    def plan_requests(self) -> list[dict]:
        return self._all(
            "select r.id::text as id, r.plan, r.kind, r.note, r.status, r.created_at, u.email, u.name, u.organization "
            "from plan_requests r join users u on u.id = r.user_id order by (r.status <> 'open'), r.created_at desc limit 200")

    def set_request_status(self, request_id: str, status: str) -> bool:
        return self._one("update plan_requests set status = %s where id::text = %s returning id",
                         (status, request_id)) is not None

    def jobs(self) -> list[dict]:
        return self._all(
            "select t.id::text as id, t.cik, t.report->>'company' as company, t.as_of, t.status, t.source, t.error, "
            "t.created_at, t.updated_at, extract(epoch from (t.updated_at - t.created_at))::int as seconds, u.email "
            "from crash_tests t left join users u on u.id = t.user_id order by t.created_at desc limit 50")

    def review_queue(self) -> list[dict]:
        return self._all(REVIEW_QUEUE_SQL)

    def add_review(self, crash_test_id: str, finding_id: str, decision: str, note: str | None, reviewer_id: str) -> str | None:
        exists = self._one("select 1 from crash_tests t, jsonb_array_elements(t.report->'findings') f "
                           "where t.id::text = %s and f->>'id' = %s", (crash_test_id, finding_id))
        if not exists:
            return None
        row = self._one("insert into finding_reviews (crash_test_id, finding_id, decision, note, reviewer_id) "
                        "values (%s, %s, %s, %s, %s) returning id::text as id",
                        (crash_test_id, finding_id, decision, note, reviewer_id))
        return row["id"]

    def demos(self) -> list[dict]:
        return self._all(
            "select t.id::text as id, t.cik, t.report->>'company' as company, t.as_of, t.decision, t.featured, t.source, "
            "t.updated_at, (t.report->'health'->>'score')::int as score, t.report->'health'->>'band' as band, u.email "
            "from crash_tests t left join users u on u.id = t.user_id where t.status = 'done' "
            "order by t.featured desc, t.updated_at desc limit 100")

    def set_featured(self, crash_test_id: str, featured: bool) -> bool:
        return self._one("update crash_tests set featured = %s where id::text = %s and status = 'done' returning id",
                         (featured, crash_test_id)) is not None
