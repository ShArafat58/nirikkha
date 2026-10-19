"""Postgres (Supabase + pgvector) connection and migrations.

Run directly:
    python -m app.db --check      # connect and show versions / tables
    python -m app.db --migrate    # apply backend/sql/*.sql in order (idempotent)
"""

from __future__ import annotations

import sys
from contextlib import contextmanager
from typing import Iterator

import psycopg

from app.config import BACKEND_DIR, get_settings

SQL_DIR = BACKEND_DIR / "sql"


class DatabaseError(RuntimeError):
    """Raised with a clear message (never containing the password)."""


@contextmanager
def connect(autocommit: bool = False) -> Iterator[psycopg.Connection]:
    url = get_settings().supabase_db_url
    if not url:
        raise DatabaseError("SUPABASE_DB_URL is not set in backend/.env.")
    try:
        conn = psycopg.connect(url, autocommit=autocommit, connect_timeout=15)
    except psycopg.OperationalError as exc:
        first_line = str(exc).strip().splitlines()[0] if str(exc).strip() else exc.__class__.__name__
        raise DatabaseError(f"Could not connect to the database: {first_line}") from exc
    try:
        yield conn
    finally:
        conn.close()


def migrate() -> list[str]:
    applied = []
    with connect(autocommit=True) as conn:
        for path in sorted(SQL_DIR.glob("*.sql")):
            conn.execute(path.read_text(encoding="utf-8"))
            applied.append(path.name)
    return applied


def check() -> dict:
    with connect() as conn:
        version = conn.execute("select split_part(version(), ' ', 2)").fetchone()[0]
        vector = conn.execute("select extversion from pg_extension where extname = 'vector'").fetchone()
        tables = {}
        for name in ("filings", "chunks"):
            exists = conn.execute("select to_regclass(%s) is not null", (f"public.{name}",)).fetchone()[0]
            tables[name] = conn.execute(f"select count(*) from {name}").fetchone()[0] if exists else None
    return {"postgres": version, "pgvector": vector[0] if vector else None, "rows": tables}


def _main(argv: list[str]) -> int:
    try:
        if "--migrate" in argv:
            for name in migrate():
                print(f"applied {name}")
        info = check()
        print(f"Postgres {info['postgres']} | pgvector {info['pgvector']}")
        for table, rows in info["rows"].items():
            print(f"  {table:8} {'missing' if rows is None else f'{rows} rows'}")
    except DatabaseError as exc:
        print(f"ERROR: {exc}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(_main(sys.argv))