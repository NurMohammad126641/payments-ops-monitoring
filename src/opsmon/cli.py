"""Command line entry point: ``opsmon list`` and ``opsmon run``."""

from __future__ import annotations

import argparse
import logging
import os
import sys
from collections.abc import Sequence

from dotenv import load_dotenv

from opsmon.alerts import build_alert, channels_from_env, dispatch
from opsmon.config import ConfigError, load_config
from opsmon.runner import run_anomalies, run_monitors, summary_table
from opsmon.sinks import CsvSink, GoogleSheetsSink, Sink

DEFAULT_CONFIG = "config/monitors.yaml"


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="opsmon",
        description="Publish payment-operations metrics and alert on anomalies.",
    )
    parser.add_argument("--config", default=DEFAULT_CONFIG, help="monitor definitions (YAML)")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("list", help="show configured monitors and anomaly rules")

    run = sub.add_parser("run", help="run monitors, publish results and send alerts")
    run.add_argument("--sink", choices=["csv", "sheets"], default="csv")
    run.add_argument("--out", default="out", help="output folder for the csv sink")
    run.add_argument("--only", nargs="+", metavar="NAME", help="run only these monitors/rules")
    run.add_argument("--no-alerts", action="store_true", help="log alerts instead of sending")
    return parser


def _make_sink(kind: str, out: str) -> Sink:
    if kind == "sheets":
        return GoogleSheetsSink(
            spreadsheet_id=os.getenv("GOOGLE_SHEETS_SPREADSHEET_ID", ""),
            credentials_file=os.getenv("GOOGLE_APPLICATION_CREDENTIALS", ""),
        )
    return CsvSink(out)


def main(argv: Sequence[str] | None = None) -> int:
    load_dotenv()
    logging.basicConfig(
        level=os.getenv("LOG_LEVEL", "INFO").upper(),
        format="%(asctime)s %(levelname)-7s %(name)s: %(message)s",
    )
    args = _build_parser().parse_args(argv)

    try:
        config = load_config(args.config)
    except ConfigError as exc:
        print(f"Config error: {exc}", file=sys.stderr)
        return 2

    if args.command == "list":
        for m in config.monitors:
            print(f"monitor  {m.name:<28} -> tab '{m.tab}'  ({m.title})")
        for a in config.anomalies:
            print(f"anomaly  {a.name:<28} ratio>={a.ratio}, min={a.min_count}  ({a.title})")
        return 0

    sink = _make_sink(args.sink, args.out)
    results = run_monitors(config, sink, only=args.only)
    anomalies, failed_rules = run_anomalies(config, only=args.only)
    failed = [r for r in results if not r.ok] + failed_rules

    print(summary_table(results))
    for anomaly in anomalies:
        print(anomaly.describe())

    alert = build_alert(anomalies, failed)
    if alert:
        subject, body = alert
        channels = [] if args.no_alerts else channels_from_env()
        if channels:
            dispatch(channels, subject, body)
        else:
            print(f"{subject}\n{body}")

    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
