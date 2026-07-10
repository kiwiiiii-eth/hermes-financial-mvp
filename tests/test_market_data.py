from __future__ import annotations

from datetime import datetime, timedelta, timezone

from app import market_data
from app.influx import parse_annotated_csv


NOW = datetime.now(timezone.utc)


class FakeReader:
    """Returns canned record lists in order, capturing each Flux query."""

    def __init__(self, responses: list[list[dict]]) -> None:
        self._responses = list(responses)
        self.queries: list[str] = []

    def query_records(self, flux: str) -> list[dict]:
        self.queries.append(flux)
        if not self._responses:
            return []
        return self._responses.pop(0)


def futures_records(
    price: float, funding: float, oi: float, volume: float, ts: datetime
) -> list[dict]:
    return [
        {"_field": "last_price", "_value": price, "_time": ts},
        {"_field": "funding_rate", "_value": funding, "_time": ts},
        {"_field": "open_interest", "_value": oi, "_time": ts},
        {"_field": "volume_24h", "_value": volume, "_time": ts},
    ]


def test_build_anomaly_input_computes_changes():
    now_records = futures_records(105.0, 0.0002, 1020.0, 5100.0, NOW)
    past_records = futures_records(100.0, 0.0001, 1000.0, 5000.0, NOW - timedelta(minutes=5))
    reader = FakeReader([now_records, past_records])

    payload = market_data.build_anomaly_input(reader, "solusdt", "5m")

    assert payload["symbol"] == "SOLUSDT"
    assert payload["current_price"] == 105.0
    assert payload["price_change_5m"] == 5.0
    assert payload["oi_change_5m"] == 2.0
    assert payload["volume_change_5m"] == 2.0
    assert payload["funding_change"] == 0.0001
    assert payload["sources"]["price"] == "binance"
    assert payload["data_quality"]["missing_fields"] == []
    assert payload["data_quality"]["stale_seconds"] is not None


def test_build_anomaly_input_falls_back_to_bitget():
    now_records = futures_records(10.0, 0.0, 500.0, 900.0, NOW)
    past_records = futures_records(10.0, 0.0, 500.0, 900.0, NOW - timedelta(minutes=5))
    reader = FakeReader([[], now_records, past_records])  # binance empty

    payload = market_data.build_anomaly_input(reader, "SOLUSDT")

    assert payload["sources"]["price"] == "bitget"
    assert 'r.exchange == "bitget"' in reader.queries[1]


def test_build_anomaly_input_returns_none_without_data():
    reader = FakeReader([[], []])
    assert market_data.build_anomaly_input(reader, "NOPEUSDT") is None


def test_build_anomaly_input_reports_missing_fields():
    now_records = [{"_field": "last_price", "_value": 10.0, "_time": NOW}]
    reader = FakeReader([now_records, []])

    payload = market_data.build_anomaly_input(reader, "SOLUSDT")

    assert payload["current_price"] == 10.0
    assert "funding_rate" in payload["data_quality"]["missing_fields"]
    assert "price_change_5m" in payload["data_quality"]["missing_fields"]


def test_build_anomaly_input_rejects_bad_window():
    reader = FakeReader([])
    try:
        market_data.build_anomaly_input(reader, "SOLUSDT", "1w")
    except ValueError as exc:
        assert "1w" in str(exc)
    else:
        raise AssertionError("expected ValueError for unsupported window")


def test_build_ma_state_groups_by_interval():
    records = [
        {"_field": "trend_score", "_value": 4, "_time": NOW, "interval": "5m"},
        {"_field": "mid_bull", "_value": True, "_time": NOW, "interval": "5m"},
        {"_field": "trend_score", "_value": 2, "_time": NOW, "interval": "1h"},
    ]
    reader = FakeReader([records])

    payload = market_data.build_ma_state(reader, "solusdt")

    assert payload["symbol"] == "SOLUSDT"
    assert payload["exchange"] == "binance"
    assert payload["intervals"]["5m"]["trend_score"] == 4
    assert payload["intervals"]["5m"]["mid_bull"] is True
    assert payload["intervals"]["1h"]["trend_score"] == 2
    assert payload["intervals"]["5m"]["candle_time"] is not None


def test_build_ma_state_returns_none_without_data():
    reader = FakeReader([[], []])
    assert market_data.build_ma_state(reader, "NOPEUSDT") is None


def test_build_latest_quotes_is_binance_only_and_includes_live_fields():
    now_records = [
        {"_field": "last_price", "_value": 105.0, "_time": NOW},
        {"_field": "mark_price", "_value": 104.9, "_time": NOW},
        {"_field": "funding_rate", "_value": 0.0002, "_time": NOW},
        {"_field": "open_interest_usd", "_value": 1_020_000.0, "_time": NOW},
        {"_field": "volume_24h", "_value": 5_100.0, "_time": NOW},
    ]
    past_records = [{"_field": "last_price", "_value": 100.0, "_time": NOW - timedelta(minutes=5)}]
    reader = FakeReader([now_records, past_records])

    payload = market_data.build_latest_quotes(reader, ["solusdt"])

    quote = payload["quotes"]["SOLUSDT"]
    assert payload["exchange"] == "binance"
    assert quote["price"] == 105.0
    assert quote["mark_price"] == 104.9
    assert quote["change_pct_5m"] == 5.0
    assert quote["open_interest_usd"] == 1_020_000.0
    assert quote["stale_seconds"] is not None
    assert all('r.exchange == "binance"' in query for query in reader.queries)


def test_parse_annotated_csv_converts_types():
    text = (
        "#group,false,false,true,true\r\n"
        "#datatype,string,long,dateTime:RFC3339,double\r\n"
        "#default,_result,,,\r\n"
        ",result,table,_time,_value\r\n"
        ",_result,0,2026-07-05T07:14:59.999Z,123.5\r\n"
        "\r\n"
    )
    records = parse_annotated_csv(text)
    assert len(records) == 1
    assert records[0]["_value"] == 123.5
    assert records[0]["_time"].year == 2026
    assert records[0]["table"] == 0
