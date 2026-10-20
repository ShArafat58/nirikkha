"""Radar persistence: alerts survive re-scans; every Approve / Reject is kept as an audit row.

    python -m app.radar.store --scan              # run both streams for all companies, save
    python -m app.radar.store --scan --no-edgar --as-of 2023-03-07
    python -m app.radar.store --list
"""
from __future__ import annotations

import argparse
import sys
from datetime import date
from typing import Protocol

PRIORITY_RANK = {"high": 0, "medium": 1, "low": 2}
DECISIONS = {"approve": "approved", "reject": "rejected"}
COLUMNS = ("id", "status", "first_seen", "last_seen", "decided_at", "decided_by_email", "note")

UPSERT_SQL = """
insert into radar_alerts (key, stream, cik, company, title, priority, payload)
values (%s, %s, %s, %s, %s, %s, %s)
on conflict (key) do update set
    stream = excluded.stream, company = excluded.company, title = excluded.title,
    priority = excluded.priority, payload = excluded.payload, last_seen = now()
"""
SELECT_SQL = """
select id::text, status, first_seen, last_seen, decided_at, decided_by_email, note, payload
from radar_alerts {where}
order by case priority when 'high' then 0 when 'medium' then 1 else 2 end, payload->>'event_date' desc
"""


def mask_email(email: str | None) -> str | None:
    if not email or "@" not in email:
        return None
    name, domain = email.split("@", 1)
    return f"{name[:1]}***@{domain}"


def _row(r) -> dict:
    out = dict(r[7])
    out.update({k: (v.isoformat() if hasattr(v, "isoformat") else v) for k, v in zip(COLUMNS, r[:7])})
    out["decided_by_email"] = mask_email(out.get("decided_by_email"))
    return out


class RadarStore(Protocol):
    def upsert(self, alerts: list[dict]) -> int: ...
    def list(self, cik: str | None = None) -> list[dict]: ...
    def get(self, alert_id: str) -> dict | None: ...
    def decide(self, alert_id: str, decision: str, note: str | None, user_id: str | None,
               user_email: str | None) -> dict | None: ...
    def history(self, alert_id: str) -> list[dict]: ...


class PostgresRadarStore:
    def upsert(self, alerts: list[dict]) -> int:
        from psycopg.types.json import Jsonb

        from app.db import connect

        with connect() as conn:
            with conn.cursor() as cur:
                cur.executemany(UPSERT_SQL, [
                    (a["key"], a["stream"], a["cik"], a["company"], a["title"], a["priority"], Jsonb(a))
                    for a in alerts])
            conn.commit()
        return len(alerts)

    def list(self, cik: str | None = None) -> list[dict]:
        from app.db import connect

        with connect() as conn:
            if cik:
                rows = conn.execute(SELECT_SQL.format(where="where cik = %s"), (cik,)).fetchall()
            else:
                rows = conn.execute(SELECT_SQL.format(where="")).fetchall()
        return [_row(r) for r in rows]

    def get(self, alert_id: str) -> dict | None:
        from app.db import connect

        with connect() as conn:
            r = conn.execute(SELECT_SQL.format(where="where id::text = %s"), (alert_id,)).fetchone()
        return _row(r) if r else None

    def decide(self, alert_id, decision, note, user_id, user_email):
        from app.db import connect

        status = DECISIONS[decision]
        with connect() as conn:
            r = conn.execute(
                "update radar_alerts set status = %s, decided_at = now(), decided_by = %s, decided_by_email = %s, "
                "note = %s where id::text = %s returning id",
                (status, user_id, user_email, note, alert_id)).fetchone()
            if not r:
                return None
            conn.execute(
                "insert into radar_decisions (alert_id, decision, note, user_id, user_email) values (%s, %s, %s, %s, %s)",
                (r[0], status, note, user_id, user_email))
            conn.commit()
        return self.get(alert_id)

    def history(self, alert_id: str) -> list[dict]:
        from app.db import connect

        with connect() as conn:
            rows = conn.execute(
                "select decision, note, user_email, created_at from radar_decisions "
                "where alert_id::text = %s order by created_at", (alert_id,)).fetchall()
        return [{"decision": r[0], "note": r[1], "by": mask_email(r[2]), "at": r[3].isoformat()} for r in rows]


class InMemoryRadarStore:
    """Same behaviour as the Postgres store, for tests and mock runs."""

    def __init__(self) -> None:
        self.rows: dict[str, dict] = {}
        self.decisions: list[dict] = []
        self._n = 0

    def upsert(self, alerts):
        for a in alerts:
            row = self.rows.get(a["key"])
            if row is None:
                self._n += 1
                self.rows[a["key"]] = {"payload": dict(a), "id": f"00000000-0000-0000-0000-{self._n:012d}",
                                       "status": "pending", "first_seen": "t0", "last_seen": "t0",
                                       "decided_at": None, "decided_by_email": None, "note": None}
            else:
                row["payload"], row["last_seen"] = dict(a), "t1"
        return len(alerts)

    def _out(self, row):
        out = dict(row["payload"])
        out.update({k: row[k] for k in COLUMNS})
        out["decided_by_email"] = mask_email(row["decided_by_email"])
        return out

    def list(self, cik=None):
        rows = [r for r in self.rows.values() if cik is None or r["payload"]["cik"] == cik]
        rows.sort(key=lambda r: r["payload"].get("event_date", ""), reverse=True)
        rows.sort(key=lambda r: PRIORITY_RANK[r["payload"]["priority"]])
        return [self._out(r) for r in rows]

    def get(self, alert_id):
        row = next((r for r in self.rows.values() if r["id"] == alert_id), None)
        return self._out(row) if row else None

    def decide(self, alert_id, decision, note, user_id, user_email):
        row = next((r for r in self.rows.values() if r["id"] == alert_id), None)
        if row is None:
            return None
        row.update({"status": DECISIONS[decision], "decided_at": "now", "decided_by_email": user_email, "note": note})
        self.decisions.append({"alert_id": alert_id, "decision": DECISIONS[decision], "note": note,
                               "by": mask_email(user_email), "at": f"t{len(self.decisions)}"})
        return self._out(row)

    def history(self, alert_id):
        return [{k: d[k] for k in ("decision", "note", "by", "at")} for d in self.decisions if d["alert_id"] == alert_id]


def main() -> int:
    parser = argparse.ArgumentParser(description="Save or list Radar alerts")
    parser.add_argument("--scan", action="store_true")
    parser.add_argument("--list", action="store_true")
    parser.add_argument("--cik", action="append")
    parser.add_argument("--as-of", type=date.fromisoformat)
    parser.add_argument("--no-edgar", action="store_true")
    args = parser.parse_args()
    store = PostgresRadarStore()
    try:
        if args.scan:
            from app.radar.engine import scan, summarise

            alerts = scan(args.cik, args.as_of, use_edgar=not args.no_edgar)
            print(f"saved {store.upsert(alerts)} alerts  {summarise(alerts)}")
        for a in store.list():
            print(f"[{a['priority'].upper():6}] {a['status']:8} {a['company'][:22]:22} {a['title'][:50]}  ({a['id'][:8]})")
    except Exception as exc:  # database errors: clear message, no traceback
        print(f"ERROR: {exc}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())