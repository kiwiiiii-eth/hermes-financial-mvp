# Skill Registry

Hermes v1.1 uses a small skill registry so the planner can route requests intentionally.

## Available

### `crypto-market-anomaly`

Status: available

Purpose:

- Read short-term crypto market features.
- Classify allowed MVP v1 anomaly types.
- Return a fixed seven-section report.

Required fields:

- `symbol`
- `current_price`
- `price_change_5m`
- `funding_rate`
- `funding_change`
- `open_interest`
- `oi_change_5m`
- `volume_change_5m`

Entrypoint:

```bash
python skills/custom/crypto-market-anomaly/handler.py --symbol BTCUSDT
```

## Planned

### `funding-analyzer`

Status: planned

Purpose:

- Funding extremes.
- Funding changes.
- Cross-exchange funding divergence.

### `open-interest-analyzer`

Status: planned

Purpose:

- OI expansion.
- OI compression.
- Price/OI divergence.

### `news-researcher`

Status: planned

Purpose:

- Source-backed market news context.
- Timestamped event explanations.

## Registry Rule

If a skill is planned but not available, Hermes must say it is unavailable and should not pretend to execute it.

