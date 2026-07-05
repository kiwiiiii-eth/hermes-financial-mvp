#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from skills.custom.crypto_market_anomaly.handler import analyze_market_anomaly  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Analyze a Hermes Financial MVP anomaly-input JSON payload.",
    )
    parser.add_argument(
        "--input-file",
        help="Path to anomaly-input JSON. If omitted, JSON is read from stdin.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print full JSON analysis instead of only telegram_message.",
    )
    args = parser.parse_args(argv)

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


if __name__ == "__main__":
    raise SystemExit(main())
