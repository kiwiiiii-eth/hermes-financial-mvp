from __future__ import annotations

import os
import secrets
from copy import deepcopy
from datetime import datetime, timezone
from typing import Any

from fastapi import Depends, FastAPI, Header, HTTPException, Query, status

from app import market_data
from app.influx import InfluxQueryError, InfluxReader
from skills.custom.crypto_market_anomaly.handler import analyze_market_anomaly


app = FastAPI(
    title="Hermes Financial MVP API",
    version="0.1.0",
    description="Read-only crypto market anomaly input API for Hermes.",
)


SAMPLE_MARKET_DATA: dict[str, dict[str, Any]] = {
    "BTCUSDT": {
        "symbol": "BTCUSDT",
        "window": "5m",
        "current_price": 108000.5,
        "price_change_5m": 1.2,
        "funding_rate": -0.0012,
        "funding_change": -0.0004,
        "open_interest": 1234567890,
        "oi_change_5m": 8.5,
        "volume_change_5m": 20.3,
        "sources": {
            "price": "binance",
            "funding": "binance",
            "open_interest": "binance",
            "history": "influxdb",
        },
        "data_quality": {
            "missing_fields": [],
            "stale_seconds": 3,
        },
    },
    "ETHUSDT": {
        "symbol": "ETHUSDT",
        "window": "5m",
        "current_price": 4200.25,
        "price_change_5m": -1.8,
        "funding_rate": 0.0009,
        "funding_change": 0.0003,
        "open_interest": 880000000,
        "oi_change_5m": -4.2,
        "volume_change_5m": 32.0,
        "sources": {
            "price": "binance",
            "funding": "binance",
            "open_interest": "binance",
            "history": "influxdb",
        },
        "data_quality": {
            "missing_fields": [],
            "stale_seconds": 5,
        },
    },
}


def get_reader() -> InfluxReader | None:
    """Live InfluxDB reader when INFLUXDB_READ_TOKEN/INFLUXDB_TOKEN is set;
    otherwise the API serves sample data so tests and local dev need no Influx."""
    return InfluxReader.from_env()


def verify_api_token(authorization: str | None = Header(default=None)) -> None:
    expected_token = os.getenv("HERMES_API_TOKEN")
    if not expected_token:
        return

    scheme, _, token = (authorization or "").partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing bearer token",
        )

    if not secrets.compare_digest(token, expected_token):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid bearer token",
        )


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/symbols")
def symbols(_: None = Depends(verify_api_token)) -> dict[str, list[str] | str]:
    reader = get_reader()
    if reader is None:
        return {"symbols": sorted(SAMPLE_MARKET_DATA), "mode": "sample"}
    try:
        return {"symbols": market_data.list_symbols(reader), "mode": "live"}
    except InfluxQueryError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


def build_market_anomaly_input(symbol: str, window: str = "5m") -> dict[str, Any]:
    normalized_symbol = symbol.upper()
    reader = get_reader()

    if reader is None:
        if normalized_symbol not in SAMPLE_MARKET_DATA:
            raise HTTPException(status_code=404, detail=f"Unknown symbol: {normalized_symbol}")
        payload = deepcopy(SAMPLE_MARKET_DATA[normalized_symbol])
        payload["window"] = window
        payload["timestamp"] = datetime.now(timezone.utc).isoformat()
        payload["mode"] = "sample"
        return payload

    try:
        payload = market_data.build_anomaly_input(reader, normalized_symbol, window)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except InfluxQueryError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    if payload is None:
        raise HTTPException(
            status_code=404,
            detail=f"No recent market data for symbol: {normalized_symbol}",
        )
    payload["mode"] = "live"
    return payload


@app.get("/market/anomaly-input")
def market_anomaly_input(
    symbol: str = Query(..., description="Trading pair, e.g. BTCUSDT"),
    window: str = Query("5m", description="Analysis window. MVP v1 supports 5m."),
    _: None = Depends(verify_api_token),
) -> dict[str, Any]:
    return build_market_anomaly_input(symbol=symbol, window=window)


@app.get("/ma/state")
def ma_state(
    symbol: str = Query(..., description="Trading pair, e.g. SOLUSDT"),
    _: None = Depends(verify_api_token),
) -> dict[str, Any]:
    reader = get_reader()
    if reader is None:
        raise HTTPException(
            status_code=503,
            detail="InfluxDB not configured; /ma/state has no sample mode.",
        )
    try:
        payload = market_data.build_ma_state(reader, symbol)
    except InfluxQueryError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    if payload is None:
        raise HTTPException(
            status_code=404, detail=f"No crypto_ma data for symbol: {symbol.upper()}"
        )
    return payload


@app.post("/analysis/anomaly")
def analysis_anomaly(
    payload: dict[str, Any],
    _: None = Depends(verify_api_token),
) -> dict[str, Any]:
    return analyze_market_anomaly(payload)


@app.get("/analyze/{symbol}")
def analyze_symbol(
    symbol: str,
    window: str = Query("5m", description="Analysis window. MVP v1 supports 5m."),
    _: None = Depends(verify_api_token),
) -> dict[str, Any]:
    market_input = build_market_anomaly_input(symbol=symbol, window=window)
    return analyze_market_anomaly(market_input)
