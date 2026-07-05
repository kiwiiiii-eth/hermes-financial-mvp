---
name: crypto-market-anomaly
description: "Use when analyzing read-only crypto market anomalies."
version: 1.0.0
author: kiwi
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [crypto, market-data, anomaly, read-only]
    related_skills: [obsidian, hermes-agent]
---

# Crypto Market Anomaly Skill

## Overview

Use this skill to analyze crypto market anomaly inputs from a read-only data API.

This skill explains abnormal Price / Funding / Open Interest conditions and formats a notification-ready response. It does not trade, predict certainty, or provide leverage advice.

Executable logic for this repo lives in two layers:

- `skills/custom/crypto-market-anomaly/handler.py` is the Hermes-callable CLI wrapper.
- `skills/custom/crypto_market_anomaly/handler.py` is the importable deterministic Python classifier used by FastAPI and tests.

## When to Use

- Use when the user asks Hermes to analyze crypto market anomalies.
- Use when given a JSON object containing `symbol`, `current_price`, `price_change_5m`, `funding_rate`, `funding_change`, `open_interest`, `oi_change_5m`, and `volume_change_5m`.
- Use when preparing a Telegram-style market anomaly report.
- Use when logging an anomaly event for later review.
- Use when a Telegram command such as `/analyze BTCUSDT` should call the read-only FastAPI API, run the handler, and return a fixed-format report.

Do not use this skill to place orders, close positions, change leverage, or produce direct trade instructions.

## Required Input

Each analysis must include:

- `symbol`
- `current_price`
- `price_change_5m`
- `funding_rate`
- `funding_change`
- `open_interest`
- `oi_change_5m`
- `volume_change_5m`

If any required field is missing, say the data is insufficient. Do not invent missing values.

## Allowed Classifications

Classify the event as exactly one of:

- `Short Squeeze`
- `Long Squeeze`
- `Funding 異常`
- `假突破`
- `無明確訊號`

If signals conflict or required data is missing, use `無明確訊號`.

## Response Format

Every response must include:

1. 現象
2. 判斷
3. 支持證據
4. 反證
5. 風險
6. 建議動作
7. 是否需要人工確認

## Classification Guide

- `Short Squeeze`: price rises quickly and OI / volume / funding suggest short covering or forced buyback.
- `Long Squeeze`: price falls quickly and OI / volume / funding suggest long deleveraging or forced selling.
- `Funding 異常`: funding_rate or funding_change is abnormal, even without a clean squeeze pattern.
- `假突破`: price breaks out, but OI, volume, or funding does not support the move, or the move quickly reverses.
- `無明確訊號`: data is insufficient, stale, contradictory, or does not match the other categories.

## Safety Rules

- Never say "一定會漲".
- Never say "一定會跌".
- Never invent data.
- If data is missing, say "資料不足".
- Default to notification only.
- Suggested actions may include observe, wait, log the event, check again, request missing data, or request human confirmation.
- Suggested actions must not include opening longs, opening shorts, adding margin, changing leverage, or placing orders.

## Example Report

```text
[Hermes 市場異常] BTCUSDT
分類：Funding 異常

1. 現象
5m price +1.2%，OI +8.5%，funding -0.12% 且 funding_change -0.04%。

2. 判斷
目前分類為 Funding 異常；不視為明確漲跌預測。

3. 支持證據
- 5m OI +8.5%
- funding -0.12%
- 5m volume +20.3%

4. 反證
price 上漲但 funding 為負，方向不一致，可能不是單純趨勢。

5. 風險
資料只代表短線異常，不代表一定延續。

6. 建議動作
只通知並記錄事件，5 分鐘後再次檢查。

7. 是否需要人工確認
需要；若要接近交易決策，必須人工確認盤口、跨所價差與資料品質。
```

## Executable Handler

Hermes can call the handler with JSON from stdin:

```bash
python skills/custom/crypto-market-anomaly/handler.py < examples/anomaly-input.json
```

For full structured output:

```bash
python skills/custom/crypto-market-anomaly/handler.py --input-file examples/anomaly-input.json --json
```

Expected flow:

```text
/analyze BTCUSDT
-> call FastAPI /market/anomaly-input?symbol=BTCUSDT&window=5m
-> pipe the returned JSON to handler.py
-> return telegram_message
-> do not trade
```

## Common Pitfalls

1. Treating anomalies as trade signals. This skill only explains market conditions.
2. Creating classifications outside the five allowed categories.
3. Filling missing values from memory or guesses.
4. Omitting counter-evidence.
5. Suggesting leverage or execution actions.

## Verification Checklist

- [ ] All required input fields are present, or the response says data is insufficient.
- [ ] `anomaly_type` is one of the five allowed classifications.
- [ ] The response includes all seven required sections.
- [ ] No certainty language is used.
- [ ] No trade execution instruction is included.
- [ ] `python skills/custom/crypto-market-anomaly/handler.py < examples/anomaly-input.json` returns a fixed report.
- [ ] `pytest -q` passes for complete data, missing data, and contradictory-signal cases.
