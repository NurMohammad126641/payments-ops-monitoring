from decimal import Decimal
from pathlib import Path

from opsmon.config import load_config
from opsmon.runner import run_anomalies, run_monitors, summary_table
from opsmon.sinks import CsvSink, MemorySink


def fake_fetcher(failing: set[str]):
    def fetch(dsn: str, sql: str):
        for name in failing:
            if name in sql:
                raise RuntimeError(f"boom in {name}")
        if "current_count" in sql:
            return ["key", "current_count", "baseline_avg"], [("ROCKET", 150, Decimal("2.5"))]
        return ["provider", "txn_count"], [("BKASH", 10), ("NAGAD", Decimal("7"))]

    return fetch


def test_runs_every_monitor_and_writes_tabs(config_path: Path, payments_dsn: str):
    config = load_config(config_path)
    sink = MemorySink()

    results = run_monitors(config, sink, fetcher=fake_fetcher(set()))

    assert all(r.ok for r in results)
    assert set(sink.tabs) == {m.tab for m in config.monitors}
    assert sink.tabs["money_flow_hourly"][0] == ["provider", "txn_count"]
    assert sink.tabs["money_flow_hourly"][2] == ["NAGAD", 7.0]


def test_one_failing_monitor_does_not_stop_the_others(config_path: Path, payments_dsn: str):
    config = load_config(config_path)
    sink = MemorySink()

    # The failure-reasons query is the only one that mentions response_message.
    results = run_monitors(config, sink, fetcher=fake_fetcher({"response_message"}))

    failed = [r for r in results if not r.ok]
    assert [r.name for r in failed] == ["failure_reasons_hourly"]
    assert "boom" in failed[0].error
    assert len(sink.tabs) == len(config.monitors) - 1


def test_only_filter(config_path: Path, payments_dsn: str):
    config = load_config(config_path)

    results = run_monitors(
        config, MemorySink(), fetcher=fake_fetcher(set()), only=["provider_success_rate"]
    )

    assert [r.name for r in results] == ["provider_success_rate"]


def test_anomalies_are_detected_from_rule_rows(config_path: Path, payments_dsn: str):
    config = load_config(config_path)

    anomalies, failed = run_anomalies(config, fetcher=fake_fetcher(set()))

    assert failed == []
    assert anomalies[0].key == "ROCKET"
    assert anomalies[0].severity == "critical"


def test_csv_sink_and_summary(tmp_path: Path, config_path: Path, payments_dsn: str):
    config = load_config(config_path)

    results = run_monitors(config, CsvSink(tmp_path), fetcher=fake_fetcher(set()))

    text = (tmp_path / "provider_success_rate.csv").read_text(encoding="utf-8")
    assert text.splitlines()[0] == "provider,txn_count"
    table = summary_table(results)
    assert "provider_success_rate" in table and "total" in table
