"""End-to-end run against the seeded demo database (demo/init): ``pytest -m integration``."""

import os
from pathlib import Path

import pytest

from opsmon.config import load_config
from opsmon.runner import run_anomalies, run_monitors
from opsmon.sinks import CsvSink

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(not os.getenv("PAYMENTS_DB_URL"), reason="PAYMENTS_DB_URL is not set"),
]


def test_all_monitors_run_against_demo_database(config_path: Path, tmp_path: Path):
    config = load_config(config_path)

    results = run_monitors(config, CsvSink(tmp_path))

    assert all(r.ok for r in results), [r.error for r in results if not r.ok]
    assert all(r.rows > 0 for r in results)
    assert (tmp_path / "provider_success_rate.csv").exists()


def test_seeded_rocket_incident_is_detected(config_path: Path):
    config = load_config(config_path)

    anomalies, failed = run_anomalies(config)

    assert failed == []
    rocket = [a for a in anomalies if a.key == "ROCKET"]
    assert rocket and rocket[0].severity == "critical"
