# Hermes Financial MVP

Hermes Financial MVP is a read-only market anomaly analysis service and Hermes skill draft for crypto market monitoring.

The first version focuses on explaining abnormal market conditions from exchange data and historical metrics. It does not place trades, predict certainty, or provide high-leverage advice.

## MVP v1 Goal

Hermes v1 only performs market anomaly analysis.

It can:

1. Read OKX / Binance real-time market data.
2. Read historical data from InfluxDB through a read-only API layer.
3. Analyze whether Price / Funding / Open Interest conditions are abnormal.
4. Report the analysis through Telegram or a similar notification channel.

It does not:

- Place orders.
- Predict that price will definitely rise or fall.
- Use data without a source.
- Provide high-leverage advice.
- Modify live trading state.
- Read or write private keys, tokens, or `.env` contents.

## Required Input Fields

Each analysis must include:

- `symbol`
- `current_price`
- `price_change_5m`
- `funding_rate`
- `funding_change`
- `open_interest`
- `oi_change_5m`
- `volume_change_5m`

If any required field is missing, Hermes must say the data is insufficient and must not invent missing values.

## Allowed Anomaly Types

Hermes v1 may only classify an event as one of:

- `Short Squeeze`
- `Long Squeeze`
- `Funding 異常`
- `假突破`
- `無明確訊號`

If the signal is unclear, contradictory, or incomplete, use `無明確訊號`.

## Required Response Format

Every response must contain:

1. 現象
2. 判斷
3. 支持證據
4. 反證
5. 風險
6. 建議動作
7. 是否需要人工確認

## Architecture

```text
Exchange APIs / InfluxDB
  -> Read-only FastAPI data layer
  -> Hermes crypto-market-anomaly skill
  -> Telegram report
  -> Markdown event log
```

## Hermes v2 Direction

This repo is the first executable app in a broader Hermes financial research agent system.

Hermes v2 should separate the core agent workflow from individual financial apps:

- Hermes Core: planner, skill router, memory, tool calling, and report integration.
- Hermes Apps / Skills: focused financial capabilities with explicit input schemas, handlers, tests, safety rules, and deployment notes.

The current app is `crypto-market-anomaly`. Candidate future apps include:

- `funding-analyzer`
- `open-interest-analyzer`
- `news-researcher`
- `etf-monitor`
- `whale-tracker`
- `risk-manager`
- `strategy-reviewer`

See [docs/hermes-v2-roadmap.md](docs/hermes-v2-roadmap.md) for the architecture direction and version path.

## Executable MVP

This repo now includes the minimal executable pieces:

```text
app/main.py
skills/custom/crypto_market_anomaly/handler.py
tests/test_crypto_market_anomaly.py
```

Run locally:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

For ServerA production, set a bearer token before starting:

```bash
export HERMES_API_TOKEN="replace-with-a-long-random-token"
uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Call the read-only API:

```bash
curl -H "Authorization: Bearer $HERMES_API_TOKEN" \
  "http://localhost:8000/market/anomaly-input?symbol=BTCUSDT&window=5m"
curl -H "Authorization: Bearer $HERMES_API_TOKEN" \
  "http://localhost:8000/analyze/BTCUSDT"
```

Run tests:

```bash
pytest -q
```

## Repository Layout

```text
app/
  main.py
docs/
  api-contract.md
  event-log-template.md
  hermes-call-flow.md
  safety-rules.md
  jetson-install.md
examples/
  anomaly-input.json
skills/
  custom/
    crypto-market-anomaly/
      SKILL.md
      handler.py
    crypto_market_anomaly/
      handler.py
tests/
  test_crypto_market_anomaly.py
```

Hermes-callable handler:

```bash
python skills/custom/crypto-market-anomaly/handler.py < examples/anomaly-input.json
```

Hermes-callable ServerA request:

```bash
export HERMES_FINANCIAL_API_URL="http://SERVER_A_HOST:8010"
export HERMES_API_TOKEN="replace-with-server-token"
python skills/custom/crypto-market-anomaly/handler.py --symbol BTCUSDT
```

## Public Safety

This repo intentionally contains no credentials, host IPs, SSH aliases, private paths, or trading API keys.

All secrets must stay in the deployment environment and be read only through environment variables or a secure secret manager.
