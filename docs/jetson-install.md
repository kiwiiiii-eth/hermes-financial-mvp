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
mkdir -p ~/.hermes/skills/custom/crypto_market_anomaly
cp skills/custom/crypto_market_anomaly/handler.py ~/.hermes/skills/custom/crypto_market_anomaly/handler.py
```

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

Deploy the FastAPI server on Server A or another data host:

```bash
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

The Jetson Hermes Agent should call:

```text
GET http://SERVER_A_HOST:8000/market/anomaly-input?symbol=BTCUSDT&window=5m
GET http://SERVER_A_HOST:8000/analyze/BTCUSDT
```

Replace `SERVER_A_HOST` with your private deployment address outside this public repo.
