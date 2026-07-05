# Hermes Planner

## Purpose

Use this skill before financial analysis when Hermes needs to decide:

- What the user is asking for.
- Which financial skill should handle the request.
- Which data fields are missing.
- Whether execution should continue or stop with a data-insufficient report.

This skill is a planning gate. It does not classify market anomalies and never places trades.

## Input

```json
{
  "user_request": "分析 BTCUSDT 是否有市場異常",
  "symbol": "BTCUSDT",
  "available_fields": [
    "symbol",
    "current_price",
    "price_change_5m",
    "funding_rate",
    "funding_change",
    "open_interest",
    "oi_change_5m",
    "volume_change_5m"
  ],
  "requested_capabilities": ["market anomaly"]
}
```

The input may also include a `data` object. Non-empty keys in `data` are treated as available fields.

## Output

The handler returns either:

- A human-readable Planner Gate report.
- Full JSON when called with `--json`.

The JSON includes:

- `selected_skill`
- `can_execute`
- `missing_fields`
- `unknown_discovery`
- `execution_plan`
- `blocked_reason`
- `needs_human_confirmation`

## Safety Rules

- Do not place orders.
- Do not make price certainty claims.
- Do not invent missing fields.
- If required fields are missing, stop before analysis.
- If a selected skill is only planned, do not pretend it exists.
- Keep secrets in environment variables or deployment secret stores only.

## Example

```bash
python skills/custom/hermes-planner/handler.py --input-file examples/planner-request.json
```

Then call the selected skill only if `can_execute=true`.

