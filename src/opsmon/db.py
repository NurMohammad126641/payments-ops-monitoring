"""Read-only access to the source databases."""

from __future__ import annotations

from typing import Any

import psycopg

DEFAULT_TIMEOUT_MS = 60_000


def fetch(
    dsn: str, sql: str, timeout_ms: int = DEFAULT_TIMEOUT_MS
) -> tuple[list[str], list[Any]]:
    """Run ``sql`` in a read-only session and return ``(column_names, rows)``.

    Every monitor opens its own short-lived connection, so a slow or failing query cannot
    block the others, and the statement timeout protects the production database.
    """
    with psycopg.connect(dsn, autocommit=True, connect_timeout=10) as conn:
        conn.execute("SET default_transaction_read_only = on")
        conn.execute(f"SET statement_timeout = {int(timeout_ms)}")
        with conn.cursor() as cur:
            cur.execute(sql)
            headers = [col.name for col in cur.description] if cur.description else []
            rows = cur.fetchall()
    return headers, rows
