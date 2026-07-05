# API Contract

Hermes should not query InfluxDB directly in MVP v1. A read-only FastAPI layer should translate exchange and InfluxDB data into stable JSON objects.

## Core Endpoint

```text
GET /market/anomaly-input?symbol=BTCUSDT&window=5m
```

Production requests should include:

```text
Authorization: Bearer <HERMES_API_TOKEN>
```

If `HERMES_API_TOKEN` is configured on the server, all data and analysis endpoints require this header. `/health` remains public for liveness checks.

## Response Schema

```json
{
  "symbol": "BTCUSDT",
  "window": "5m",
  "timestamp": "2026-07-05T11:30:00+08:00",
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
    "history": "influxdb"
  },
  "data_quality": {
    "missing_fields": [],
    "stale_seconds": 3
  }
}
```

## Data Rules

- `current_price` must include a source.
- `funding_rate` and `funding_change` must use consistent units.
- `open_interest` must have a documented unit in the API implementation.
- `data_quality.missing_fields` must list missing required fields.
- Hermes must not fill missing values by inference.

## Optional Endpoints

```text
GET /health
GET /symbols
GET /market/latest?symbol=BTCUSDT
GET /market/history?symbol=BTCUSDT&window=1h&interval=1m
POST /analysis/anomaly
GET /analyze/BTCUSDT
```

`POST /analysis/anomaly` is optional. It can be used to store completed analysis outputs, but it must not trade.

The executable MVP includes:

- `GET /health`
- `GET /symbols`
- `GET /market/anomaly-input`
- `POST /analysis/anomaly`
- `GET /analyze/{symbol}`

## Authentication

Set `HERMES_API_TOKEN` in the ServerA environment:

```bash
export HERMES_API_TOKEN="replace-with-a-long-random-token"
```

Then call protected endpoints with:

```bash
curl -H "Authorization: Bearer $HERMES_API_TOKEN" \
  "http://SERVER_A_HOST:8000/market/anomaly-input?symbol=BTCUSDT&window=5m"
```

Do not commit real token values.
