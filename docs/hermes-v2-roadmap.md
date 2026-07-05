# Hermes v2 Roadmap

Hermes v2 should grow from a single market anomaly MVP into a financial research agent operating system.

The current `crypto-market-anomaly` skill remains the first production app. Future work should add new apps without forcing every feature into the core runtime.

## Product Positioning

Hermes is an AI agent operating system for financial research.

It should help collect read-only market evidence, route work to the right skill, produce conservative reports, and preserve reusable memory. It should not become an automatic trading executor.

## Core Responsibilities

Hermes Core owns the shared agent workflow:

1. Planner
   - Understand the user request.
   - Decide whether a single skill is enough or whether several skills are needed.
   - Keep the default action as research and notification.

2. Router
   - Map a request to a registered skill.
   - Prefer explicit skill contracts over ad hoc prompting.
   - Refuse unsupported tasks instead of inventing unavailable tools.

3. Memory
   - Read project context, operating rules, event logs, and prior decisions.
   - Write reusable market events and lessons back to Markdown or another approved memory store.
   - Never store secrets, private keys, tokens, or `.env` contents.

4. Tools
   - Call approved APIs, terminal commands, and data services.
   - Keep financial data access read-only by default.
   - Use environment variables or deployment secrets for credentials.

5. Reporter
   - Normalize output into predictable sections.
   - Preserve evidence, counter-evidence, risk, and human-confirmation status.
   - Avoid certainty language and unsupported trading advice.

## App / Skill Model

Each Hermes financial app should own its own contract:

- Skill name and use cases.
- Input schema.
- Output schema.
- Handler implementation.
- Safety rules.
- Tests.
- Example inputs.
- Deployment notes.
- Memory or event-log format.

The core should not need custom logic for every new app. A new app should be added by registering a skill contract and handler.

## Current App

`crypto-market-anomaly`

Purpose:

- Read ServerA market anomaly input from a read-only FastAPI layer.
- Classify short-term market conditions into the allowed MVP v1 anomaly types.
- Return a seven-section report.
- Notify only; do not trade.

Status:

- FastAPI service exists.
- Bearer token protection exists.
- Jetson Hermes can call the handler.
- The handler can fetch ServerA data through `--symbol`.
- Tests cover complete data, missing data, contradictory signals, token protection, and ServerA fetch mode.

## Candidate Future Apps

1. `funding-analyzer`
   - Track funding extremes, funding changes, and cross-exchange funding divergence.

2. `open-interest-analyzer`
   - Track OI expansion, OI compression, and price/OI divergences.

3. `news-researcher`
   - Connect market events to timestamped news and source-backed narratives.

4. `etf-monitor`
   - Track ETF flow, premium/discount, market calendar, and related macro context.

5. `whale-tracker`
   - Track large transfers or wallet activity from approved data sources.

6. `risk-manager`
   - Review risk, data quality, alert severity, and whether human confirmation is required.

7. `strategy-reviewer`
   - Review historical event logs and strategy assumptions without placing trades.

## Version Path

### v1: Executable Market Anomaly MVP

Done:

- `crypto-market-anomaly` skill contract.
- Executable FastAPI API layer.
- Executable Hermes-callable handler.
- ServerA deployment.
- Jetson skill installation.
- Token-protected API calls.
- Fixed seven-section report.

### v1.1: Operational Polish

Next:

- Add a direct Telegram or Discord command path such as `/analyze BTCUSDT`.
- Write each completed report to a Markdown event log.
- Add a lightweight skill registry document.
- Add deployment health checks and restart notes.
- Connect the API to live InfluxDB query helpers instead of sample payloads.

### v2: Financial Agent OS

Next major architecture:

- Shared skill registry.
- Shared schema conventions.
- Planner and router prompt/rules.
- Memory protocol for project notes and market event logs.
- Reporter protocol for evidence-based financial reports.
- Multiple apps callable through the same Hermes workflow.

## Non-Goals

- No automatic trading.
- No direct high-leverage advice.
- No private-key or exchange-secret handling.
- No hidden or unsourced market data.
- No certainty claims such as "must rise" or "must fall".
- No direct InfluxDB access from Hermes if a read-only API layer can provide stable JSON.

## Success Criteria

Hermes v2 is successful when a user can ask a financial research question, Hermes can route it to the right approved skill, fetch sourced data through read-only tools, produce a conservative evidence-based report, and write a reusable memory entry without modifying the core for every new app.
