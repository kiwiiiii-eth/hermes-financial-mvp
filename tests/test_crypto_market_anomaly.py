import json
import subprocess
import sys
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from fastapi.testclient import TestClient

from app.main import app
from skills.custom.crypto_market_anomaly.handler import analyze_market_anomaly


client = TestClient(app)


def complete_payload():
    return {
        "symbol": "BTCUSDT",
        "current_price": 108000.5,
        "price_change_5m": 1.2,
        "funding_rate": -0.0012,
        "funding_change": -0.0004,
        "open_interest": 1234567890,
        "oi_change_5m": 8.5,
        "volume_change_5m": 20.3,
        "sources": {
            "price": "binance",
            "funding": "binance",
            "open_interest": "binance",
            "history": "influxdb",
        },
        "data_quality": {
            "missing_fields": [],
            "stale_seconds": 3,
        },
    }


def test_complete_data_returns_fixed_report_sections():
    result = analyze_market_anomaly(complete_payload())

    assert result["anomaly_type"] == "Funding 異常"
    assert result["needs_human_confirmation"] is True
    assert "一定會漲" not in result["telegram_message"]
    assert "一定會跌" not in result["telegram_message"]
    for section in ["1. 現象", "2. 判斷", "3. 支持證據", "4. 反證", "5. 風險", "6. 建議動作", "7. 是否需要人工確認"]:
        assert section in result["telegram_message"]


def test_missing_data_returns_insufficient_data():
    payload = complete_payload()
    del payload["funding_rate"]

    result = analyze_market_anomaly(payload)

    assert result["anomaly_type"] == "無明確訊號"
    assert "funding_rate" in result["data_quality"]["missing_fields"]
    assert "資料不足" in result["telegram_message"]
    assert "自行補資料" in result["counter_evidence"][0]


def test_contradictory_signal_uses_unclear_classification():
    payload = complete_payload()
    payload.update(
        {
            "price_change_5m": 0.2,
            "funding_rate": 0.0001,
            "funding_change": 0.0,
            "oi_change_5m": 0.1,
            "volume_change_5m": 1.0,
        }
    )

    result = analyze_market_anomaly(payload)

    assert result["anomaly_type"] == "無明確訊號"
    assert "無明確訊號" in result["telegram_message"]


def test_fastapi_market_anomaly_input_endpoint():
    response = client.get("/market/anomaly-input", params={"symbol": "BTCUSDT"})

    assert response.status_code == 200
    data = response.json()
    assert data["symbol"] == "BTCUSDT"
    assert data["data_quality"]["missing_fields"] == []


def test_fastapi_analyze_symbol_endpoint():
    response = client.get("/analyze/BTCUSDT")

    assert response.status_code == 200
    data = response.json()
    assert data["symbol"] == "BTCUSDT"
    assert data["anomaly_type"] in {
        "Short Squeeze",
        "Long Squeeze",
        "Funding 異常",
        "假突破",
        "無明確訊號",
    }


def test_api_token_required_when_configured(monkeypatch):
    monkeypatch.setenv("HERMES_API_TOKEN", "test-token")

    response = client.get("/market/anomaly-input", params={"symbol": "BTCUSDT"})

    assert response.status_code == 401


def test_api_token_accepts_valid_bearer_token(monkeypatch):
    monkeypatch.setenv("HERMES_API_TOKEN", "test-token")

    response = client.get(
        "/market/anomaly-input",
        params={"symbol": "BTCUSDT"},
        headers={"Authorization": "Bearer test-token"},
    )

    assert response.status_code == 200
    assert response.json()["symbol"] == "BTCUSDT"


def test_api_token_rejects_invalid_bearer_token(monkeypatch):
    monkeypatch.setenv("HERMES_API_TOKEN", "test-token")

    response = client.get(
        "/market/anomaly-input",
        params={"symbol": "BTCUSDT"},
        headers={"Authorization": "Bearer wrong-token"},
    )

    assert response.status_code == 403


def test_skill_handler_cli_reads_stdin_and_prints_report():
    handler = Path("skills/custom/crypto-market-anomaly/handler.py")
    proc = subprocess.run(
        [sys.executable, str(handler)],
        input=json.dumps(complete_payload()),
        text=True,
        capture_output=True,
        check=True,
    )

    assert "[Hermes 市場異常] BTCUSDT" in proc.stdout
    assert "分類：Funding 異常" in proc.stdout
    assert "7. 是否需要人工確認" in proc.stdout


def test_skill_handler_cli_json_mode(tmp_path):
    input_file = tmp_path / "payload.json"
    input_file.write_text(json.dumps(complete_payload()), encoding="utf-8")

    handler = Path("skills/custom/crypto-market-anomaly/handler.py")
    proc = subprocess.run(
        [sys.executable, str(handler), "--input-file", str(input_file), "--json"],
        text=True,
        capture_output=True,
        check=True,
    )
    result = json.loads(proc.stdout)

    assert result["symbol"] == "BTCUSDT"
    assert result["anomaly_type"] == "Funding 異常"
    assert result["needs_human_confirmation"] is True


def test_skill_handler_cli_fetches_api_payload(monkeypatch):
    import skills.custom.crypto_market_anomaly.handler as analyzer

    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def read(self):
            return json.dumps(complete_payload()).encode("utf-8")

    captured = {}

    def fake_urlopen(request, timeout):
        captured["url"] = request.full_url
        captured["authorization"] = request.headers.get("Authorization")
        captured["timeout"] = timeout
        return FakeResponse()

    wrapper_path = Path("skills/custom/crypto-market-anomaly/handler.py")
    wrapper_globals = {"__file__": str(wrapper_path)}
    exec(wrapper_path.read_text(encoding="utf-8"), wrapper_globals)
    monkeypatch.setitem(wrapper_globals, "analyze_market_anomaly", analyzer.analyze_market_anomaly)
    monkeypatch.setitem(wrapper_globals, "urlopen", fake_urlopen)

    code = wrapper_globals["main"](
        [
            "--symbol",
            "btcusdt",
            "--api-url",
            "http://server-a.local:8010",
            "--token",
            "test-token",
            "--json",
        ]
    )

    parsed = urlparse(captured["url"])
    query = parse_qs(parsed.query)
    assert code == 0
    assert parsed.path == "/market/anomaly-input"
    assert query["symbol"] == ["BTCUSDT"]
    assert query["window"] == ["5m"]
    assert captured["authorization"] == "Bearer test-token"
