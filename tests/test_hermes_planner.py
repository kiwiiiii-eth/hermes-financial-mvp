import json
import subprocess
import sys
from pathlib import Path

from skills.custom.hermes_planner.handler import plan_financial_task


def complete_planner_payload():
    return {
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
            "volume_change_5m",
        ],
        "requested_capabilities": ["market anomaly"],
    }


def test_planner_routes_complete_market_anomaly_request():
    result = plan_financial_task(complete_planner_payload())

    assert result["planner_version"] == "v1.1"
    assert result["selected_skill"] == "crypto-market-anomaly"
    assert result["can_execute"] is True
    assert result["missing_fields"] == []
    assert result["blocked_reason"] is None
    assert "不下單" in result["report"]


def test_planner_blocks_missing_required_fields():
    payload = complete_planner_payload()
    payload["available_fields"].remove("funding_rate")

    result = plan_financial_task(payload)

    assert result["selected_skill"] == "crypto-market-anomaly"
    assert result["can_execute"] is False
    assert result["missing_fields"] == ["funding_rate"]
    assert "資料不足" in result["blocked_reason"]
    assert result["needs_human_confirmation"] is True


def test_planner_treats_data_keys_as_available_fields():
    payload = {
        "user_request": "分析 BTCUSDT 是否有市場異常",
        "symbol": "BTCUSDT",
        "data": {
            "symbol": "BTCUSDT",
            "current_price": 108000.5,
            "price_change_5m": 1.2,
            "funding_rate": -0.0012,
            "funding_change": -0.0004,
            "open_interest": 1234567890,
            "oi_change_5m": 8.5,
            "volume_change_5m": 20.3,
        },
    }

    result = plan_financial_task(payload)

    assert result["can_execute"] is True
    assert result["missing_fields"] == []


def test_planner_reports_planned_skill_as_unavailable():
    payload = {
        "user_request": "幫我查 BTCUSDT 新聞",
        "symbol": "BTCUSDT",
        "available_fields": ["symbol"],
        "requested_capabilities": ["news"],
    }

    result = plan_financial_task(payload)

    assert result["selected_skill"] == "news-researcher"
    assert result["skill_status"] == "planned"
    assert result["can_execute"] is False
    assert "尚未實作" in result["blocked_reason"]


def test_planner_cli_reads_stdin_and_prints_report():
    handler = Path("skills/custom/hermes-planner/handler.py")
    proc = subprocess.run(
        [sys.executable, str(handler)],
        input=json.dumps(complete_planner_payload()),
        text=True,
        capture_output=True,
        check=True,
    )

    assert "[Hermes Planner Gate] BTCUSDT" in proc.stdout
    assert "選擇 Skill：crypto-market-anomaly" in proc.stdout


def test_planner_cli_json_mode(tmp_path):
    input_file = tmp_path / "planner.json"
    input_file.write_text(json.dumps(complete_planner_payload()), encoding="utf-8")

    handler = Path("skills/custom/hermes-planner/handler.py")
    proc = subprocess.run(
        [sys.executable, str(handler), "--input-file", str(input_file), "--json"],
        text=True,
        capture_output=True,
        check=True,
    )
    result = json.loads(proc.stdout)

    assert result["selected_skill"] == "crypto-market-anomaly"
    assert result["can_execute"] is True
