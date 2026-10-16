"""Where monitor results are published.

* :class:`CsvSink` writes one CSV per tab: handy for local runs, CI artifacts and debugging.
* :class:`GoogleSheetsSink` replaces a tab in a Google Sheet that Looker Studio reads from.
* :class:`MemorySink` keeps results in memory for tests.
"""

from __future__ import annotations

import csv
import threading
from collections.abc import Sequence
from pathlib import Path
from typing import Any, Protocol

from opsmon.cells import to_rows

SHEETS_SCOPE = "https://www.googleapis.com/auth/spreadsheets"


class Sink(Protocol):
    def write(self, tab: str, headers: Sequence[str], rows: Sequence[Sequence[Any]]) -> None: ...


class CsvSink:
    def __init__(self, out_dir: str | Path) -> None:
        self.out_dir = Path(out_dir)
        self.out_dir.mkdir(parents=True, exist_ok=True)

    def write(self, tab: str, headers: Sequence[str], rows: Sequence[Sequence[Any]]) -> None:
        path = self.out_dir / f"{tab}.csv"
        with path.open("w", newline="", encoding="utf-8") as fh:
            writer = csv.writer(fh)
            writer.writerow(headers)
            writer.writerows(to_rows(rows))


class MemorySink:
    def __init__(self) -> None:
        self.tabs: dict[str, list[list[Any]]] = {}
        self._lock = threading.Lock()

    def write(self, tab: str, headers: Sequence[str], rows: Sequence[Sequence[Any]]) -> None:
        with self._lock:
            self.tabs[tab] = [list(headers), *to_rows(rows)]


class GoogleSheetsSink:
    """Clear a tab and write the latest result, using a Google service account.

    A service account (instead of a personal OAuth token) is what you want for a scheduled job:
    nothing expires, nothing needs a browser, and access is limited to the sheets you share with
    the service account's email address.
    """

    def __init__(self, spreadsheet_id: str, credentials_file: str | Path) -> None:
        from google.oauth2 import service_account

        if not spreadsheet_id:
            raise ValueError("GOOGLE_SHEETS_SPREADSHEET_ID is not set")
        self.spreadsheet_id = spreadsheet_id
        self._credentials = service_account.Credentials.from_service_account_file(
            str(credentials_file), scopes=[SHEETS_SCOPE]
        )

    def write(self, tab: str, headers: Sequence[str], rows: Sequence[Sequence[Any]]) -> None:
        from googleapiclient.discovery import build

        # googleapiclient objects are not thread-safe, so each write builds its own client.
        service = build("sheets", "v4", credentials=self._credentials, cache_discovery=False)
        values = service.spreadsheets().values()
        values.clear(spreadsheetId=self.spreadsheet_id, range=f"'{tab}'").execute()
        values.update(
            spreadsheetId=self.spreadsheet_id,
            range=f"'{tab}'!A1",
            valueInputOption="RAW",
            body={"values": [list(headers), *to_rows(rows)]},
        ).execute()
