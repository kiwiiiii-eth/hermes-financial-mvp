# Hermes Call Flow

This is the MVP interaction flow for a Telegram-style command.

```text
Telegram command: /analyze BTCUSDT
  -> Hermes receives symbol BTCUSDT
  -> Hermes calls FastAPI /market/anomaly-input?symbol=BTCUSDT&window=5m
  -> FastAPI returns anomaly-input JSON
  -> handler.py analyzes and classifies the event
  -> Hermes returns the fixed seven-section report
  -> No trade is placed
```

## Minimal API Call

```bash
curl "http://SERVER_A_HOST:8000/market/anomaly-input?symbol=BTCUSDT&window=5m"
```

## Minimal Analysis Call

```bash
curl "http://SERVER_A_HOST:8000/analyze/BTCUSDT"
```

## Hermes-Callable Handler

Hermes can call the executable skill handler directly after fetching JSON from the API:

```bash
curl -s "http://SERVER_A_HOST:8000/market/anomaly-input?symbol=BTCUSDT&window=5m" \
  | python skills/custom/crypto-market-anomaly/handler.py
```

For structured JSON output:

```bash
curl -s "http://SERVER_A_HOST:8000/market/anomaly-input?symbol=BTCUSDT&window=5m" \
  | python skills/custom/crypto-market-anomaly/handler.py --json
```

## Local Development

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## Safety Invariant

The flow ends at a report. It must not place orders, close positions, change leverage, or mutate live trading state.
