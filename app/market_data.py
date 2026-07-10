from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from app.influx import InfluxReader

BUCKET = "exchange"
EXCHANGE_PREFERENCE = ("binance", "bitget")

FUTURES_FIELDS = (
    "last_price",
    "mark_price",
    "funding_rate",
    "open_interest",
    "open_interest_usd",
    "volume_24h",
    "bid_price",
    "ask_price",
)

MA_INTERVALS = ("5m", "15m", "1h", "4h", "1d")


def _field_filter(fields: tuple[str, ...]) -> str:
    return " or ".join(f'r._field == "{field}"' for field in fields)


def _escape(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"')


def _last_snapshot_flux(
    symbol: str, exchange: str, start: str, stop: str | None = None
) -> str:
    stop_clause = f", stop: {stop}" if stop else ""
    return (
        f'from(bucket: "{BUCKET}")\n'
        f"  |> range(start: {start}{stop_clause})\n"
        f'  |> filter(fn: (r) => r._measurement == "crypto_futures"'
        f' and r.symbol == "{_escape(symbol)}" and r.exchange == "{_escape(exchange)}")\n'
        f"  |> filter(fn: (r) => {_field_filter(FUTURES_FIELDS)})\n"
        f"  |> last()"
    )


def _snapshot(records: list[dict[str, Any]]) -> dict[str, Any]:
    """Collapse per-field last() records into {field: value} plus newest _time."""
    snapshot: dict[str, Any] = {}
    latest: datetime | None = None
    for record in records:
        field = record.get("_field")
        if not field:
            continue
        snapshot[field] = record.get("_value")
        ts = record.get("_time")
        if isinstance(ts, datetime) and (latest is None or ts > latest):
            latest = ts
    snapshot["_latest_time"] = latest
    return snapshot


def _pct_change(now: float | None, past: float | None) -> float | None:
    if now is None or past is None or past == 0:
        return None
    return round((now - past) / abs(past) * 100, 4)


def _window_minutes(window: str) -> int:
    if not window.endswith("m") or not window[:-1].isdigit():
        raise ValueError(f"Unsupported window: {window!r} (expected e.g. '5m')")
    minutes = int(window[:-1])
    if not 1 <= minutes <= 60:
        raise ValueError(f"Window out of range: {window!r}")
    return minutes


def build_anomaly_input(
    reader: InfluxReader, symbol: str, window: str = "5m"
) -> dict[str, Any] | None:
    """Build the /market/anomaly-input payload from live crypto_futures data.

    Returns None when no exchange has recent data for the symbol.
    """
    symbol = symbol.upper()
    minutes = _window_minutes(window)

    now_snap: dict[str, Any] = {}
    exchange_used: str | None = None
    for exchange in EXCHANGE_PREFERENCE:
        candidate = _snapshot(
            reader.query_records(_last_snapshot_flux(symbol, exchange, start="-3m"))
        )
        if candidate.get("last_price") is not None:
            now_snap = candidate
            exchange_used = exchange
            break
    if exchange_used is None:
        return None

    # A ~3 minute band around "window minutes ago" tolerates collector gaps.
    past_snap = _snapshot(
        reader.query_records(
            _last_snapshot_flux(
                symbol,
                exchange_used,
                start=f"-{minutes + 2}m",
                stop=f"-{max(minutes - 1, 1)}m",
            )
        )
    )

    now_utc = datetime.now(timezone.utc)
    latest_time = now_snap.get("_latest_time")
    stale_seconds = (
        int((now_utc - latest_time).total_seconds())
        if isinstance(latest_time, datetime)
        else None
    )

    funding_now = now_snap.get("funding_rate")
    funding_past = past_snap.get("funding_rate")
    funding_change = (
        round(funding_now - funding_past, 8)
        if funding_now is not None and funding_past is not None
        else None
    )

    payload: dict[str, Any] = {
        "symbol": symbol,
        "window": window,
        "timestamp": now_utc.isoformat(),
        "current_price": now_snap.get("last_price"),
        "price_change_5m": _pct_change(
            now_snap.get("last_price"), past_snap.get("last_price")
        ),
        "funding_rate": funding_now,
        "funding_change": funding_change,
        "open_interest": now_snap.get("open_interest"),
        "oi_change_5m": _pct_change(
            now_snap.get("open_interest"), past_snap.get("open_interest")
        ),
        "volume_change_5m": _pct_change(
            now_snap.get("volume_24h"), past_snap.get("volume_24h")
        ),
        "sources": {
            "price": exchange_used,
            "funding": exchange_used,
            "open_interest": exchange_used,
            "history": "influxdb",
        },
    }

    required = (
        "current_price",
        "price_change_5m",
        "funding_rate",
        "funding_change",
        "open_interest",
        "oi_change_5m",
        "volume_change_5m",
    )
    payload["data_quality"] = {
        "missing_fields": [field for field in required if payload[field] is None],
        "stale_seconds": stale_seconds,
    }
    return payload


def _ma_state_flux(symbol: str, exchange: str) -> str:
    return (
        f'from(bucket: "{BUCKET}")\n'
        f"  |> range(start: -3d)\n"
        f'  |> filter(fn: (r) => r._measurement == "crypto_ma"'
        f' and r.symbol == "{_escape(symbol)}" and r.exchange == "{_escape(exchange)}")\n'
        f"  |> last()"
    )


def build_ma_state(reader: InfluxReader, symbol: str) -> dict[str, Any] | None:
    """Build the /ma/state payload from crypto_ma. Returns None when absent."""
    symbol = symbol.upper()
    for exchange in EXCHANGE_PREFERENCE:
        records = reader.query_records(_ma_state_flux(symbol, exchange))
        if not records:
            continue

        intervals: dict[str, dict[str, Any]] = {}
        for record in records:
            interval = record.get("interval")
            field = record.get("_field")
            if not interval or not field:
                continue
            entry = intervals.setdefault(interval, {})
            entry[field] = record.get("_value")
            ts = record.get("_time")
            if isinstance(ts, datetime):
                existing = entry.get("_candle_time")
                if existing is None or ts > existing:
                    entry["_candle_time"] = ts

        for entry in intervals.values():
            candle_time = entry.pop("_candle_time", None)
            entry["candle_time"] = (
                candle_time.isoformat() if isinstance(candle_time, datetime) else None
            )

        return {
            "symbol": symbol,
            "exchange": exchange,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "intervals": {
                interval: intervals[interval]
                for interval in MA_INTERVALS
                if interval in intervals
            },
        }
    return None


def list_symbols(reader: InfluxReader, exchange: str | None = None) -> list[str]:
    exchange_filter = (
        f' and r.exchange == "{_escape(exchange)}"' if exchange else ""
    )
    flux = (
        'import "influxdata/influxdb/schema"\n'
        f'schema.tagValues(bucket: "{BUCKET}", tag: "symbol",'
        f' predicate: (r) => r._measurement == "crypto_futures"{exchange_filter}, start: -1h)'
    )
    records = reader.query_records(flux)
    return sorted(
        {record["_value"] for record in records if record.get("_value")}
    )


def build_latest_quotes(
    reader: InfluxReader, symbols: list[str], exchange: str = "binance"
) -> dict[str, Any]:
    """Return compact, read-only latest quotes for the Live Activity bridge.

    This endpoint deliberately reads only the existing ``crypto_futures``
    measurement. It never talks to an exchange account and never exposes an
    Influx credential to callers.
    """
    quotes: dict[str, Any] = {}
    for raw_symbol in symbols:
        symbol = raw_symbol.upper().strip()
        if not symbol:
            continue
        now_snap = _snapshot(
            reader.query_records(_last_snapshot_flux(symbol, exchange, start="-3m"))
        )
        price = now_snap.get("last_price")
        if price is None:
            continue

        past_snap = _snapshot(
            reader.query_records(
                _last_snapshot_flux(symbol, exchange, start="-7m", stop="-4m")
            )
        )
        latest_time = now_snap.get("_latest_time")
        stale_seconds = (
            int((datetime.now(timezone.utc) - latest_time).total_seconds())
            if isinstance(latest_time, datetime)
            else None
        )
        quotes[symbol] = {
            "symbol": symbol,
            "price": price,
            "mark_price": now_snap.get("mark_price"),
            "change_pct_5m": _pct_change(price, past_snap.get("last_price")),
            "funding_rate": now_snap.get("funding_rate"),
            "open_interest_usd": now_snap.get("open_interest_usd"),
            "volume_24h": now_snap.get("volume_24h"),
            "ts": latest_time.isoformat() if isinstance(latest_time, datetime) else None,
            "stale_seconds": stale_seconds,
        }
    return {
        "exchange": exchange,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "quotes": quotes,
    }
