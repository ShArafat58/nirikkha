"""Demo checkout store (sql/009_billing.sql). The plan change and the simulated payment are one transaction."""

from __future__ import annotations

from psycopg.rows import dict_row

from app.db import connect

RECORD_COLUMNS = "id::text as id, plan, method, amount_usd::float as amount_usd, reference, status, created_at"


class PostgresBillingStore:
    def subscribe(self, user_id: str, plan: str, method: str, amount_usd: float, reference: str) -> dict:
        with connect() as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute("update users set plan = %s where id::text = %s", (plan, user_id))
                cur.execute(f"insert into payment_simulations (user_id, plan, method, amount_usd, reference) "
                            f"values (%s, %s, %s, %s, %s) returning {RECORD_COLUMNS}",
                            (user_id, plan, method, amount_usd, reference))
                row = cur.fetchone()
            conn.commit()
        return row

    def history(self, user_id: str) -> list[dict]:
        with connect(autocommit=True) as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute(f"select {RECORD_COLUMNS} from payment_simulations where user_id::text = %s "
                            f"order by created_at desc limit 50", (user_id,))
                return cur.fetchall()