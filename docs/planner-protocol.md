# Planner Protocol

Hermes v1.1 adds a Planner Gate before financial skills run.

The planner is not an analyst and not a trader. Its job is to decide whether Hermes has enough information to call a skill, which skill should be called, and what should happen if data is missing.

## Flow

```text
User
  -> Hermes Planner Gate
  -> Unknown Discovery
  -> Skill Router
  -> Financial Skill
  -> Reporter
  -> Memory / Event Log
```

## Planner Input

```json
{
  "user_request": "分析 BTCUSDT 是否有市場異常",
  "symbol": "BTCUSDT",
  "available_fields": ["symbol", "current_price"],
  "requested_capabilities": ["market anomaly"]
}
```

The planner may also receive a `data` object. Non-empty keys in `data` are treated as available fields.

## Planner Output

The planner returns:

- `selected_skill`
- `can_execute`
- `missing_fields`
- `unknown_discovery`
- `execution_plan`
- `blocked_reason`
- `needs_human_confirmation`

If `can_execute=false`, Hermes should stop and report why.

## Rules

- Plan before executing.
- Prefer explicit skill contracts over ad hoc prompting.
- If required fields are missing, do not call the downstream analyzer.
- If a selected skill is still planned, report that it is unavailable.
- Never invent missing data.
- Never use the planner as a trading executor.

## First Supported Route

`crypto-market-anomaly` is the first executable route.

It requires:

- `symbol`
- `current_price`
- `price_change_5m`
- `funding_rate`
- `funding_change`
- `open_interest`
- `oi_change_5m`
- `volume_change_5m`

