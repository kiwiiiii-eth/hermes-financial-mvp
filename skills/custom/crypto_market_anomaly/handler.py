from __future__ import annotations

from dataclasses import dataclass
from typing import Any


REQUIRED_FIELDS = (
    "symbol",
    "current_price",
    "price_change_5m",
    "funding_rate",
    "funding_change",
    "open_interest",
    "oi_change_5m",
    "volume_change_5m",
)

ALLOWED_ANOMALY_TYPES = (
    "Short Squeeze",
    "Long Squeeze",
    "Funding 異常",
    "假突破",
    "無明確訊號",
)


@dataclass(frozen=True)
class MarketFeatures:
    symbol: str
    current_price: float
    price_change_5m: float
    funding_rate: float
    funding_change: float
    open_interest: float
    oi_change_5m: float
    volume_change_5m: float


def analyze_market_anomaly(payload: dict[str, Any]) -> dict[str, Any]:
    missing_fields = _missing_required_fields(payload)
    data_quality = _data_quality(payload, missing_fields)

    if missing_fields:
        return _build_response(
            symbol=str(payload.get("symbol", "UNKNOWN")),
            anomaly_type="無明確訊號",
            phenomenon=f"資料不足，缺少必要欄位：{', '.join(missing_fields)}。",
            judgement="資料不足，無法完成 Hermes Financial MVP v1 市場異常分類。",
            supporting_evidence=[],
            counter_evidence=["必要欄位缺失，不能自行補資料。"],
            risk="若在資料缺失時做判斷，容易把資料品質問題誤判成市場訊號。",
            suggested_action="補齊缺失欄位後再分析；目前只記錄資料不足事件。",
            needs_human_confirmation=True,
            data_quality=data_quality,
        )

    features = _parse_features(payload)
    anomaly_type = _classify(features)
    sections = _sections_for(features, anomaly_type)
    return _build_response(
        symbol=features.symbol,
        anomaly_type=anomaly_type,
        data_quality=data_quality,
        **sections,
    )


def _missing_required_fields(payload: dict[str, Any]) -> list[str]:
    missing = []
    for field in REQUIRED_FIELDS:
        value = payload.get(field)
        if value is None or value == "":
            missing.append(field)
    return missing


def _data_quality(payload: dict[str, Any], missing_fields: list[str]) -> dict[str, Any]:
    raw_quality = payload.get("data_quality") or {}
    return {
        "missing_fields": missing_fields or list(raw_quality.get("missing_fields", [])),
        "stale_seconds": raw_quality.get("stale_seconds"),
        "sources": payload.get("sources", {}),
    }


def _parse_features(payload: dict[str, Any]) -> MarketFeatures:
    return MarketFeatures(
        symbol=str(payload["symbol"]).upper(),
        current_price=float(payload["current_price"]),
        price_change_5m=float(payload["price_change_5m"]),
        funding_rate=float(payload["funding_rate"]),
        funding_change=float(payload["funding_change"]),
        open_interest=float(payload["open_interest"]),
        oi_change_5m=float(payload["oi_change_5m"]),
        volume_change_5m=float(payload["volume_change_5m"]),
    )


def _classify(features: MarketFeatures) -> str:
    price = features.price_change_5m
    oi = features.oi_change_5m
    funding = features.funding_rate
    funding_change = features.funding_change
    volume = features.volume_change_5m

    if abs(funding) >= 0.001 or abs(funding_change) >= 0.0003:
        if abs(price) < 0.8 or price * funding < 0:
            return "Funding 異常"

    if price >= 1.0 and oi <= -2.0 and volume >= 10.0:
        return "Short Squeeze"

    if price <= -1.0 and oi <= -2.0 and volume >= 10.0:
        return "Long Squeeze"

    if abs(price) >= 1.0 and volume < 5.0:
        return "假突破"

    if abs(price) >= 1.0 and abs(oi) < 0.5:
        return "假突破"

    return "無明確訊號"


def _sections_for(features: MarketFeatures, anomaly_type: str) -> dict[str, Any]:
    evidence = [
        f"current_price={features.current_price}",
        f"price_change_5m={features.price_change_5m:+.2f}%",
        f"funding_rate={features.funding_rate:+.4f}",
        f"funding_change={features.funding_change:+.4f}",
        f"open_interest={features.open_interest:.0f}",
        f"oi_change_5m={features.oi_change_5m:+.2f}%",
        f"volume_change_5m={features.volume_change_5m:+.2f}%",
    ]

    if anomaly_type == "Short Squeeze":
        judgement = "分類為 Short Squeeze；目前只代表空頭回補壓力跡象，不代表一定上漲。"
        counter = ["仍需確認盤口與跨所價格；單一 5m 視窗可能只是短線噪音。"]
    elif anomaly_type == "Long Squeeze":
        judgement = "分類為 Long Squeeze；目前只代表多頭去槓桿跡象，不代表一定下跌。"
        counter = ["若 OI 下降後價格快速收回，可能只是短線洗盤而非延續行情。"]
    elif anomaly_type == "Funding 異常":
        judgement = "分類為 Funding 異常；funding 與價格/OI 狀態需要人工確認。"
        counter = ["Funding 異常不等於方向訊號，可能只是持倉成本短暫偏離。"]
    elif anomaly_type == "假突破":
        judgement = "分類為假突破；價格移動缺少 OI 或 volume 支持。"
        counter = ["若後續 volume 與 OI 補上，分類可能需要重新評估。"]
    else:
        judgement = "分類為無明確訊號；資料完整但訊號未形成一致結論。"
        counter = ["Price、Funding、OI 或 volume 沒有形成足夠一致的異常型態。"]

    return {
        "phenomenon": (
            f"{features.symbol} 5m price {features.price_change_5m:+.2f}%，"
            f"OI {features.oi_change_5m:+.2f}%，funding {features.funding_rate:+.4f}，"
            f"volume {features.volume_change_5m:+.2f}%。"
        ),
        "judgement": judgement,
        "supporting_evidence": evidence,
        "counter_evidence": counter,
        "risk": "這是短線異常分析，不是交易指令；資料延遲、交易所差異與流動性都可能造成誤判。",
        "suggested_action": "只通知並記錄事件；必要時補查盤口、跨所價差與下一個 5m 視窗。",
        "needs_human_confirmation": True,
    }


def _build_response(
    *,
    symbol: str,
    anomaly_type: str,
    phenomenon: str,
    judgement: str,
    supporting_evidence: list[str],
    counter_evidence: list[str],
    risk: str,
    suggested_action: str,
    needs_human_confirmation: bool,
    data_quality: dict[str, Any],
) -> dict[str, Any]:
    if anomaly_type not in ALLOWED_ANOMALY_TYPES:
        anomaly_type = "無明確訊號"

    telegram_message = _format_report(
        symbol=symbol,
        anomaly_type=anomaly_type,
        phenomenon=phenomenon,
        judgement=judgement,
        supporting_evidence=supporting_evidence,
        counter_evidence=counter_evidence,
        risk=risk,
        suggested_action=suggested_action,
        needs_human_confirmation=needs_human_confirmation,
    )

    return {
        "symbol": symbol,
        "anomaly_type": anomaly_type,
        "phenomenon": phenomenon,
        "judgement": judgement,
        "supporting_evidence": supporting_evidence,
        "counter_evidence": counter_evidence,
        "risk": risk,
        "suggested_action": suggested_action,
        "needs_human_confirmation": needs_human_confirmation,
        "data_quality": data_quality,
        "telegram_message": telegram_message,
        "next_check_minutes": 5,
    }


def _format_report(
    *,
    symbol: str,
    anomaly_type: str,
    phenomenon: str,
    judgement: str,
    supporting_evidence: list[str],
    counter_evidence: list[str],
    risk: str,
    suggested_action: str,
    needs_human_confirmation: bool,
) -> str:
    evidence_text = "\n".join(f"- {item}" for item in supporting_evidence) or "- 資料不足"
    counter_text = "\n".join(f"- {item}" for item in counter_evidence) or "- 無"
    human = "需要" if needs_human_confirmation else "不需要"
    return (
        f"[Hermes 市場異常] {symbol}\n"
        f"分類：{anomaly_type}\n\n"
        f"1. 現象\n{phenomenon}\n\n"
        f"2. 判斷\n{judgement}\n\n"
        f"3. 支持證據\n{evidence_text}\n\n"
        f"4. 反證\n{counter_text}\n\n"
        f"5. 風險\n{risk}\n\n"
        f"6. 建議動作\n{suggested_action}\n\n"
        f"7. 是否需要人工確認\n{human}"
    )
