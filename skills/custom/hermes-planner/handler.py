#!/usr/bin/env python3
from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path
from typing import Any


def _load_planner():
    here = Path(__file__).resolve()

    repo_root = here.parents[3]
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))

    try:
        from skills.custom.hermes_planner.handler import plan_financial_task

        return plan_financial_task
    except ModuleNotFoundError:
        pass

    sibling_handler = here.parent.parent / "hermes_planner" / "handler.py"
    if sibling_handler.exists():
        spec = importlib.util.spec_from_file_location("hermes_planner_runtime", sibling_handler)
        if spec and spec.loader:
            module = importlib.util.module_from_spec(spec)
            sys.modules[spec.name] = module
            spec.loader.exec_module(module)
            return module.plan_financial_task

    raise SystemExit(
        "Cannot locate planner. Install the full repo or copy "
        "skills/custom/hermes_planner next to this skill."
    )


plan_financial_task = _load_planner()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Plan a Hermes financial research task.")
    parser.add_argument(
        "--input-file",
        help="Path to planner request JSON. If omitted, JSON is read from stdin.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print full JSON plan instead of the human-readable report.",
    )
    args = parser.parse_args(argv)

    payload = _load_payload(args.input_file)
    result = plan_financial_task(payload)

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(result["report"])

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
