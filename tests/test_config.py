from pathlib import Path

import pytest

from opsmon.config import ConfigError, load_config


def test_loads_shipped_config(config_path: Path, payments_dsn: str):
    config = load_config(config_path)

    assert {m.name for m in config.monitors} >= {"money_flow_hourly", "provider_success_rate"}
    assert config.anomalies[0].ratio == 1.5
    assert config.dsn("payments") == payments_dsn
    assert "SELECT" in config.monitors[0].sql().upper()


def test_missing_env_var_is_a_clear_error(config_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv("PAYMENTS_DB_URL", raising=False)
    config = load_config(config_path)

    with pytest.raises(ConfigError, match="PAYMENTS_DB_URL"):
        config.dsn("payments")


def _write(tmp_path: Path, body: str) -> Path:
    (tmp_path / "sql").mkdir()
    (tmp_path / "sql" / "q.sql").write_text("SELECT 1;", encoding="utf-8")
    path = tmp_path / "monitors.yaml"
    path.write_text(body, encoding="utf-8")
    return path


def test_rejects_duplicate_names(tmp_path: Path):
    path = _write(
        tmp_path,
        """
sources: {db: DB_URL}
monitors:
  - {name: a, source: db, query: q.sql}
  - {name: a, source: db, query: q.sql}
""",
    )
    with pytest.raises(ConfigError, match="Duplicate"):
        load_config(path)


def test_rejects_unknown_source(tmp_path: Path):
    path = _write(
        tmp_path,
        """
sources: {db: DB_URL}
monitors:
  - {name: a, source: other, query: q.sql}
""",
    )
    with pytest.raises(ConfigError, match="unknown source"):
        load_config(path)


def test_rejects_missing_query_file(tmp_path: Path):
    path = _write(
        tmp_path,
        """
sources: {db: DB_URL}
monitors:
  - {name: a, source: db, query: missing.sql}
""",
    )
    with pytest.raises(ConfigError, match="not found"):
        load_config(path)


def test_rejects_ratio_not_above_one(tmp_path: Path):
    path = _write(
        tmp_path,
        """
sources: {db: DB_URL}
anomalies:
  - {name: spike, source: db, query: q.sql, ratio: 1}
""",
    )
    with pytest.raises(ConfigError, match="ratio"):
        load_config(path)
