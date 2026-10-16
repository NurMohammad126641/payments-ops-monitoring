"""Run monitors in parallel and isolate failures."""

from __future__ import annotations

import logging
import time
from collections.abc import Callable, Iterable
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from typing import Any

from opsmon import db
from opsmon.anomaly import Anomaly, detect
from opsmon.config import AnomalyRule, Config, Monitor
from opsmon.sinks import Sink

log = logging.getLogger(__name__)

Fetcher = Callable[[str, str], tuple[list[str], list[Any]]]


@dataclass(frozen=True)
class MonitorResult:
    name: str
    ok: bool
    rows: int = 0
    seconds: float = 0.0
    error: str | None = None


def _run_monitor(monitor: Monitor, config: Config, sink: Sink, fetcher: Fetcher) -> MonitorResult:
    start = time.perf_counter()
    try:
        headers, rows = fetcher(config.dsn(monitor.source), monitor.sql())
        sink.write(monitor.tab, headers, rows)
    except Exception as exc:
        log.exception("Monitor %s failed", monitor.name)
        return MonitorResult(
            monitor.name, False, seconds=time.perf_counter() - start, error=_short(exc)
        )
    elapsed = time.perf_counter() - start
    log.info("Monitor %s: %d rows in %.2fs", monitor.name, len(rows), elapsed)
    return MonitorResult(monitor.name, True, rows=len(rows), seconds=elapsed)


def run_monitors(
    config: Config,
    sink: Sink,
    fetcher: Fetcher = db.fetch,
    only: Iterable[str] | None = None,
) -> list[MonitorResult]:
    """Run every monitor (or just ``only``) concurrently and return one result per monitor."""
    wanted = set(only or [])
    monitors = [m for m in config.monitors if not wanted or m.name in wanted]
    if not monitors:
        return []
    results: list[MonitorResult] = []
    with ThreadPoolExecutor(max_workers=max(1, config.max_workers)) as pool:
        futures = [pool.submit(_run_monitor, m, config, sink, fetcher) for m in monitors]
        for future in as_completed(futures):
            results.append(future.result())
    return sorted(results, key=lambda r: r.name)


def run_anomalies(
    config: Config,
    fetcher: Fetcher = db.fetch,
    only: Iterable[str] | None = None,
) -> tuple[list[Anomaly], list[MonitorResult]]:
    """Evaluate the anomaly rules. Returns ``(anomalies, failed_rules)``."""
    wanted = set(only or [])
    rules: list[AnomalyRule] = [a for a in config.anomalies if not wanted or a.name in wanted]
    anomalies: list[Anomaly] = []
    failed: list[MonitorResult] = []
    for rule in rules:
        start = time.perf_counter()
        try:
            _, rows = fetcher(config.dsn(rule.source), rule.sql())
        except Exception as exc:
            log.exception("Anomaly rule %s failed", rule.name)
            elapsed = time.perf_counter() - start
            failed.append(MonitorResult(rule.name, False, seconds=elapsed, error=_short(exc)))
            continue
        anomalies.extend(detect(rule.name, rows, ratio=rule.ratio, min_count=rule.min_count))
    return anomalies, failed


def summary_table(results: Iterable[MonitorResult]) -> str:
    """A fixed-width summary like the old "timing summary" email, for logs and alerts."""
    rows = list(results)
    if not rows:
        return "No monitors ran."
    width = max(len(r.name) for r in rows)
    lines = [f"{'monitor'.ljust(width)}  status  rows    seconds"]
    for r in rows:
        status = "ok" if r.ok else "FAILED"
        lines.append(f"{r.name.ljust(width)}  {status:<6}  {r.rows:<6}  {r.seconds:>7.2f}")
    total = sum(r.seconds for r in rows)
    lines.append(f"{'total'.ljust(width)}  {'':<6}  {'':<6}  {total:>7.2f}")
    return "\n".join(lines)


def _short(exc: BaseException) -> str:
    text = f"{type(exc).__name__}: {exc}".strip()
    return text if len(text) <= 300 else text[:297] + "..."
