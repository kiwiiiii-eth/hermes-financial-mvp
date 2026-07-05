#!/usr/bin/env python3
from __future__ import annotations

import argparse
import importlib.util
import json
import os
import sys
from pathlib import Path
from typing import Any
from urllib.parse import urlencode
from urllib.request import Request, urlopen


def _load_analyzer():
    here = Path(__file__).resolve()

    # Repo checkout layout:
    #   <repo>/skills/custom/crypto-market-anomaly/handler.py
    repo_root = here.parents[3]
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))

    try:
        from skills.custom.crypto_market_anomaly.handler import analyze_market_anomaly

        return analyze_market_anomaly
    except ModuleNotFoundError:
        pass

    # Hermes user-local skill layout:
    #   ~/.hermes/skills/custom/crypto-market-anomaly/handler.py
    #   ~/.hermes/skills/custom/crypto_market_anomaly/handler.py
    sibling_handler = here.parent.parent / "crypto_market_anomaly" / "handler.py"
    if sibling_handler.exists():
        spec = importlib.util.spec_from_file_location(
            "crypto_market_anomaly_runtime",
            sibling_handler,
        )
        if spec and spec.loader:
            module = importlib.util.module_from_spec(spec)
            sys.modules[spec.name] = module
            spec.loader.exec_module(module)
            return module.analyze_market_anomaly

    raise SystemExit(
        "Cannot locate analyzer. Install the full repo or copy "
        "skills/custom/crypto_market_anomaly next to this skill."
    )


analyze_market_anomaly = _load_analyzer()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Analyze a Hermes Financial MVP anomaly-input JSON payload.",
    )
    parser.add_argument(
        "--input-file",
        help="Path to anomaly-input JSON. If omitted, JSON is read from stdin.",
    )
    parser.add_argument(
        "--symbol",
        help="Fetch anomaly-input JSON from HERMES_FINANCIAL_API_URL for this symbol.",
    )
    parser.add_argument(
        "--window",
        default="5m",
        help="Analysis window for --symbol mode. Default: 5m.",
    )
    parser.add_argument(
        "--api-url",
        default=os.getenv("HERMES_FINANCIAL_API_URL", ""),
        help="Base FastAPI URL. Defaults to HERMES_FINANCIAL_API_URL.",
    )
    parser.add_argument(
        "--token",
        default=os.getenv("HERMES_API_TOKEN", ""),
        help="Bearer token. Defaults to HERMES_API_TOKEN.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print full JSON analysis instead of only telegram_message.",
    )
    args = parser.parse_args(argv)

    if args.symbol:
        payload = _fetch_payload(
            api_url=args.api_url,
            token=args.token,
            symbol=args.symbol,
            window=args.window,
        )
    else:
        payload = _load_payload(args.input_file)
    result = analyze_market_anomaly(payload)

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(result["telegram_message"])

    return 0


def _load_payload(input_file: str | None) -> dict[str, Any]:
    if input_file:
        raw = Path(input_file).read_text(encoding="utf-8")
    else:
        raw = sys.stdin.read()

    if not raw.strip():
        raise SystemExit("No JSON payload provided. Use --input-file or pipe JSON to stdin.")

    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise SystemExit(f"Invalid JSON payload: {exc}") from exc

    if not isinstance(payload, dict):
        raise SystemExit("JSON payload must be an object.")

    return payload


def _fetch_payload(*, api_url: str, token: str, symbol: str, window: str) -> dict[str, Any]:
    if not api_url:
        raise SystemExit("Missing API URL. Set HERMES_FINANCIAL_API_URL or pass --api-url.")
    if not token:
        raise SystemExit("Missing bearer token. Set HERMES_API_TOKEN or pass --token.")

    base = api_url.rstrip("/")
    query = urlencode({"symbol": symbol.upper(), "window": window})
    request = Request(
        f"{base}/market/anomaly-input?{query}",
        headers={"Authorization": f"Bearer {token}"},
    )
    try:
        with urlopen(request, timeout=10) as response:
            raw = response.read().decode("utf-8")
    except Exception as exc:
        raise SystemExit(f"Failed to fetch anomaly input: {exc}") from exc

    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise SystemExit(f"API returned invalid JSON: {exc}") from exc

    if not isinstance(payload, dict):
        raise SystemExit("API response must be a JSON object.")

    return payload


if __name__ == "__main__":
    raise SystemExit(main())
