# Jetson Install Guide

This guide describes a generic Jetson deployment pattern for a local Hermes installation.

Do not commit machine-specific SSH aliases, IP addresses, usernames, tokens, or private paths to this public repo.

## Target Skill Path

For a user-local Hermes skill:

```text
~/.hermes/skills/custom/crypto-market-anomaly/SKILL.md
```

## Install

From this repo:

```bash
mkdir -p ~/.hermes/skills/custom/crypto-market-anomaly
cp skills/custom/crypto-market-anomaly/SKILL.md ~/.hermes/skills/custom/crypto-market-anomaly/SKILL.md
```

If you also want the executable Python handler available on the Jetson machine:

```bash
cp skills/custom/crypto-market-anomaly/handler.py ~/.hermes/skills/custom/crypto-market-anomaly/handler.py
```

If you deploy the full repo on Jetson, the wrapper imports the shared classifier from `skills/custom/crypto_market_anomaly/handler.py`.

## Verify

```bash
hermes skills list | grep crypto-market-anomaly
```

If `hermes` is not on PATH in a non-interactive SSH session, use the full path to the local Hermes binary.

## Test Load

```bash
hermes --skills crypto-market-anomaly -z "Analyze this sample BTCUSDT anomaly input using MVP v1 format."
```

The current Hermes session may not see newly created skills immediately. Start a new session if needed.

## Server A FastAPI

Deploy the FastAPI server on Server A or another data host. Prefer binding to localhost or a private interface, then expose it to Jetson through SSH tunnel, VPN, or a locked-down reverse proxy.

```bash
pip install -r requirements.txt
export HERMES_API_TOKEN="replace-with-a-long-random-token"
uvicorn app.main:app --host 127.0.0.1 --port 8000
```

The Jetson Hermes Agent should call:

```text
GET http://SERVER_A_HOST:8000/market/anomaly-input?symbol=BTCUSDT&window=5m
GET http://SERVER_A_HOST:8000/analyze/BTCUSDT
```

Replace `SERVER_A_HOST` with your private deployment address outside this public repo.

Hermes can also fetch the JSON and pipe it into the handler:

```bash
curl -s -H "Authorization: Bearer $HERMES_API_TOKEN" \
  "http://SERVER_A_HOST:8000/market/anomaly-input?symbol=BTCUSDT&window=5m" \
  | python ~/.hermes/skills/custom/crypto-market-anomaly/handler.py
```

## Network Exposure

Recommended order:

1. ServerA FastAPI binds to `127.0.0.1`.
2. Jetson reaches it through SSH tunnel or private VPN.
3. If a public reverse proxy is unavoidable, require HTTPS, bearer token, firewall allowlist, and rate limiting.

Do not use Zeabur as a public relay for this MVP unless there is a specific reason and the same authentication and firewall rules are applied.
