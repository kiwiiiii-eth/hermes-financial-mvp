from __future__ import annotations

import csv
import io
import os
from datetime import datetime
from typing import Any

import httpx


class InfluxQueryError(Exception):
    """Raised when InfluxDB is unreachable or returns an error."""


class InfluxReader:
    """Read-only Flux query client for InfluxDB 2.x over the HTTP API.

    Uses the raw /api/v2/query endpoint (annotated CSV) so the API server
    only needs httpx, which is already a project dependency.
    """

    def __init__(self, url: str, org: str, token: str, timeout: float = 10.0) -> None:
        self.url = url.rstrip("/")
        self.org = org
        self._token = token
        self._timeout = timeout

    @classmethod
    def from_env(cls) -> InfluxReader | None:
        token = os.getenv("INFLUXDB_READ_TOKEN") or os.getenv("INFLUXDB_TOKEN")
        if not token:
            return None
        return cls(
            url=os.getenv("INFLUXDB_URL", "http://localhost:8086"),
            org=os.getenv("INFLUXDB_ORG", "crypto"),
            token=token,
        )

    def query_records(self, flux: str) -> list[dict[str, Any]]:
        try:
            response = httpx.post(
                f"{self.url}/api/v2/query",
                params={"org": self.org},
                headers={
                    "Authorization": f"Token {self._token}",
                    "Content-Type": "application/vnd.flux",
                    "Accept": "application/csv",
                },
                content=flux,
                timeout=self._timeout,
            )
        except httpx.HTTPError as exc:
            raise InfluxQueryError(f"InfluxDB unreachable: {exc}") from exc

        if response.status_code != 200:
            raise InfluxQueryError(
                f"InfluxDB query failed ({response.status_code}): {response.text[:300]}"
            )
        return parse_annotated_csv(response.text)


def parse_annotated_csv(text: str) -> list[dict[str, Any]]:
    """Parse InfluxDB annotated CSV into one dict per record.

    Values in the _value column are converted according to the #datatype
    annotation; _time/_start/_stop are parsed to datetime.
    """
    records: list[dict[str, Any]] = []
    datatypes: list[str] = []
    columns: list[str] = []

    for row in csv.reader(io.StringIO(text)):
        if not row or all(cell == "" for cell in row):
            columns = []
            continue
        if row[0].startswith("#"):
            if row[0] == "#datatype":
                datatypes = row
                columns = []
            continue
        if not columns:
            columns = row
            continue

        record: dict[str, Any] = {}
        for i, name in enumerate(columns):
            if not name or i >= len(row):
                continue
            record[name] = _convert(row[i], datatypes[i] if i < len(datatypes) else "string")
        records.append(record)

    return records


def _convert(value: str, datatype: str) -> Any:
    if value == "":
        return None
    if datatype == "double":
        return float(value)
    if datatype in ("long", "unsignedLong"):
        return int(value)
    if datatype == "boolean":
        return value == "true"
    if datatype.startswith("dateTime"):
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return value
    return value
