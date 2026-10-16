"""Load and validate the monitor definitions from YAML.

Connection strings and other secrets never live in the YAML file: each data source names the
environment variable that holds its DSN, so the same config can run on a laptop, in CI or on a
server.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


class ConfigError(ValueError):
    """Raised when the monitor configuration is missing or invalid."""


@dataclass(frozen=True)
class Monitor:
    """A SQL query whose result is published to one sheet tab."""

    name: str
    title: str
    source: str
    query_file: Path
    tab: str

    def sql(self) -> str:
        return self.query_file.read_text(encoding="utf-8")


@dataclass(frozen=True)
class AnomalyRule:
    """A SQL query returning ``(key, current_count, baseline_avg)`` rows to compare."""

    name: str
    title: str
    source: str
    query_file: Path
    ratio: float = 1.5
    min_count: int = 20

    def sql(self) -> str:
        return self.query_file.read_text(encoding="utf-8")


@dataclass(frozen=True)
class Config:
    sources: dict[str, str]
    monitors: list[Monitor] = field(default_factory=list)
    anomalies: list[AnomalyRule] = field(default_factory=list)
    max_workers: int = 6

    def dsn(self, source: str) -> str:
        """Return the connection string for ``source`` from its environment variable."""
        env_var = self.sources.get(source)
        if env_var is None:
            raise ConfigError(f"Unknown data source '{source}'")
        value = os.getenv(env_var)
        if not value:
            raise ConfigError(f"Environment variable {env_var} is not set (source '{source}')")
        return value


def _require(item: dict[str, Any], key: str, where: str) -> Any:
    if key not in item or item[key] in (None, ""):
        raise ConfigError(f"{where}: missing required key '{key}'")
    return item[key]


def _query_path(sql_dir: Path, name: str, where: str) -> Path:
    path = (sql_dir / name).resolve()
    if not path.is_file():
        raise ConfigError(f"{where}: query file not found: {path}")
    return path


def load_config(path: str | Path) -> Config:
    """Parse ``path`` and return a validated :class:`Config`."""
    path = Path(path)
    if not path.is_file():
        raise ConfigError(f"Config file not found: {path}")

    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    sql_dir = (path.parent / raw.get("sql_dir", "sql")).resolve()

    sources = raw.get("sources") or {}
    if not sources:
        raise ConfigError("At least one data source is required under 'sources'")

    monitors: list[Monitor] = []
    for item in raw.get("monitors") or []:
        name = _require(item, "name", "monitor")
        where = f"monitor '{name}'"
        source = _require(item, "source", where)
        if source not in sources:
            raise ConfigError(f"{where}: unknown source '{source}'")
        monitors.append(
            Monitor(
                name=name,
                title=item.get("title", name),
                source=source,
                query_file=_query_path(sql_dir, _require(item, "query", where), where),
                tab=item.get("tab", name),
            )
        )

    anomalies: list[AnomalyRule] = []
    for item in raw.get("anomalies") or []:
        name = _require(item, "name", "anomaly rule")
        where = f"anomaly rule '{name}'"
        source = _require(item, "source", where)
        if source not in sources:
            raise ConfigError(f"{where}: unknown source '{source}'")
        ratio = float(item.get("ratio", 1.5))
        if ratio <= 1:
            raise ConfigError(f"{where}: ratio must be greater than 1")
        anomalies.append(
            AnomalyRule(
                name=name,
                title=item.get("title", name),
                source=source,
                query_file=_query_path(sql_dir, _require(item, "query", where), where),
                ratio=ratio,
                min_count=int(item.get("min_count", 20)),
            )
        )

    names = [m.name for m in monitors] + [a.name for a in anomalies]
    duplicates = sorted({n for n in names if names.count(n) > 1})
    if duplicates:
        raise ConfigError(f"Duplicate names: {', '.join(duplicates)}")

    return Config(
        sources=dict(sources),
        monitors=monitors,
        anomalies=anomalies,
        max_workers=int(raw.get("max_workers", 6)),
    )
