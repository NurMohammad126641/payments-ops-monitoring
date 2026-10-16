"""Flag metrics that run well above their historical baseline.

The production version compared "not successful" transactions in the current hour with the
average for the same hour over the previous four weeks. The comparison itself is plain Python so
it can be unit tested without a database.
"""

from __future__ import annotations

import math
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class Anomaly:
    rule: str
    key: str
    current: float
    baseline: float
    ratio: float
    severity: str  # "warning" or "critical"

    def describe(self) -> str:
        times = "new" if math.isinf(self.ratio) else f"{self.ratio:.1f}x"
        return (
            f"[{self.severity.upper()}] {self.rule} / {self.key}: {self.current:g} now vs "
            f"{self.baseline:.1f} usual ({times})"
        )


def detect(
    rule: str,
    rows: Iterable[Sequence[Any]],
    ratio: float = 1.5,
    min_count: int = 20,
) -> list[Anomaly]:
    """Return anomalies for rows shaped ``(key, current_count, baseline_avg)``.

    A row is anomalous when ``current >= min_count`` and ``current / baseline >= ratio``.
    It is *critical* when the observed ratio is at least twice the threshold, or when there is
    no baseline at all. ``min_count`` stops tiny numbers (1 failure vs 0.2 usual) from paging
    anyone.
    """
    found: list[Anomaly] = []
    for key, current, baseline in rows:
        current_f = float(current or 0)
        baseline_f = float(baseline or 0)
        if current_f < min_count:
            continue
        observed = current_f / baseline_f if baseline_f > 0 else math.inf
        if observed < ratio:
            continue
        severity = "critical" if observed >= ratio * 2 else "warning"
        found.append(
            Anomaly(
                rule=rule,
                key=str(key),
                current=current_f,
                baseline=baseline_f,
                ratio=observed if math.isinf(observed) else round(observed, 2),
                severity=severity,
            )
        )
    return sorted(found, key=lambda a: a.ratio, reverse=True)
