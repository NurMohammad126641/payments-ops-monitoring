from __future__ import annotations

from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def config_path() -> Path:
    return ROOT / "config" / "monitors.yaml"


@pytest.fixture
def payments_dsn(monkeypatch: pytest.MonkeyPatch) -> str:
    dsn = "postgresql://demo:demo@localhost:5432/payments"
    monkeypatch.setenv("PAYMENTS_DB_URL", dsn)
    return dsn
