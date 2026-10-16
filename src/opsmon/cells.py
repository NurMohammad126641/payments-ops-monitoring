"""Convert database values into plain cells that CSV files and Google Sheets accept."""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from datetime import date, datetime, time
from decimal import Decimal
from typing import Any
from uuid import UUID


def to_cell(value: Any) -> str | int | float:
    if value is None:
        return ""
    if isinstance(value, bool):
        return str(value).lower()
    if isinstance(value, int | float | str):
        return value
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, datetime | date | time):
        return value.isoformat()
    if isinstance(value, UUID):
        return str(value)
    return str(value)


def to_rows(rows: Iterable[Sequence[Any]]) -> list[list[str | int | float]]:
    return [[to_cell(v) for v in row] for row in rows]
