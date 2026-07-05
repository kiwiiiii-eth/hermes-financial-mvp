from __future__ import annotations

from dataclasses import dataclass
from typing import Any


MARKET_ANOMALY_FIELDS = (
    "symbol",
    "current_price",
    "price_change_5m",
    "funding_rate",
    "funding_change",
    "open_interest",
    "oi_change_5m",
    "volume_change_5m",
)

DEFAULT_REGISTRY: dict[str, dict[str, Any]] = {
    "crypto-market-anomaly": {
        "status": "available",
        "purpose": "read-only short-term crypto market anomaly analysis",
        "required_fields": MARKET_ANOMALY_FIELDS,
        "entrypoint": "skills/custom/crypto-market-anomaly/handler.py",
        "safe_actions": ("notify", "record_event", "request_human_confirmation"),
    },
    "funding-analyzer": {
        "status": "planned",
        "purpose": "funding extreme and funding divergence analysis",
        "required_fields": ("symbol", "funding_rate", "funding_change"),
        "safe_actions": ("research", "notify"),
    },
    "open-interest-analyzer": {
        "status": "planned",
        "purpose": "open interest expansion, compression, and price/OI divergence analysis",
        "required_fields": ("symbol", "open_interest", "oi_change_5m"),
        "safe_actions": ("research", "notify"),
    },
    "news-researcher": {
        "status": "planned",
        "purpose": "source-backed news context for market events",
        "required_fields": ("symbol", "time_window", "news_sources"),
        "safe_actions": ("research", "cite_sources"),
    },
}


@dataclass(frozen=True)
class PlannerRequest:
    user_request: str
    symbol: str | None
    available_fields: set[str]
    requested_capabilities: set[str]


def plan_financial_task(payload: dict[str, Any]) -> dict[str, Any]:
    request = _parse_request(payload)
    selected_skill = _select_skill(request)
    registry_entry = DEFAULT_REGISTRY[selected_skill]
    required_fields = tuple(registry_entry["required_fields"])
    missing_fields = [field for field in required_fields if field not in request.available_fields]
    unknowns = _discover_unknowns(request=request, selected_skill=selected_skill, missing_fields=missing_fields)
    can_execute = registry_entry["status"] == "available" and not missing_fields
    needs_human_confirmation = bool(missing_fields or unknowns["missing_research_context"])

    steps = [
        "確認使用者請求與 symbol。",
        "檢查必要欄位與資料來源。",
        f"路由到 {selected_skill}。",
        "要求 skill 只輸出固定格式報告，不下單。",
        "將結果回報並視需要寫入事件記憶。",
    ]

    if missing_fields:
        steps.insert(2, "資料不足時停止分析並回報缺失欄位。")

    return {
        "planner_version": "v1.1",
        "user_request": request.user_request,
        "symbol": request.symbol or "UNKNOWN",
        "selected_skill": selected_skill,
        "skill_status": registry_entry["status"],
        "can_execute": can_execute,
        "required_fields": list(required_fields),
        "available_fields": sorted(request.available_fields),
        "missing_fields": missing_fields,
        "unknown_discovery": unknowns,
        "execution_plan": steps,
        "safe_actions": list(registry_entry["safe_actions"]),
        "blocked_reason": _blocked_reason(registry_entry["status"], missing_fields),
        "needs_human_confirmation": needs_human_confirmation,
        "report": _format_plan_report(
            symbol=request.symbol or "UNKNOWN",
            selected_skill=selected_skill,
            can_execute=can_execute,
            missing_fields=missing_fields,
            unknowns=unknowns,
            steps=steps,
        ),
    }


def _parse_request(payload: dict[str, Any]) -> PlannerRequest:
    user_request = str(payload.get("user_request") or payload.get("query") or "").strip()
    symbol = payload.get("symbol")
    if symbol is not None:
        symbol = str(symbol).upper()

    available_fields = set()
    raw_available = payload.get("available_fields") or []
    if isinstance(raw_available, dict):
        available_fields.update(field for field, value in raw_available.items() if value is not None)
    else:
        available_fields.update(str(field) for field in raw_available)

    data = payload.get("data")
    if isinstance(data, dict):
        available_fields.update(field for field, value in data.items() if value is not None and value != "")

    requested_capabilities = set(str(item).lower() for item in payload.get("requested_capabilities", []))
    lowered_request = user_request.lower()
    for capability in ("funding", "oi", "open interest", "news", "macro", "on-chain", "whale"):
        if capability in lowered_request:
            requested_capabilities.add(capability)

    return PlannerRequest(
        user_request=user_request,
        symbol=symbol,
        available_fields=available_fields,
        requested_capabilities=requested_capabilities,
    )


def _select_skill(request: PlannerRequest) -> str:
    capabilities = request.requested_capabilities
    text = request.user_request.lower()

    if "news" in capabilities and "market anomaly" not in text and "異常" not in text:
        return "news-researcher"
    if {"funding"} & capabilities and not ({"oi", "open interest"} & capabilities):
        return "funding-analyzer"
    if {"oi", "open interest"} & capabilities and "funding" not in capabilities:
        return "open-interest-analyzer"

    return "crypto-market-anomaly"


def _discover_unknowns(
    *,
    request: PlannerRequest,
    selected_skill: str,
    missing_fields: list[str],
) -> dict[str, Any]:
    missing_context = []
    capabilities = request.requested_capabilities

    if request.symbol is None:
        missing_context.append("symbol")
    if "news" in capabilities and "news_sources" not in request.available_fields:
        missing_context.append("news_sources")
    if "macro" in capabilities and "macro_context" not in request.available_fields:
        missing_context.append("macro_context")
    if ("on-chain" in capabilities or "whale" in capabilities) and "onchain_sources" not in request.available_fields:
        missing_context.append("onchain_sources")

    return {
        "questions": [
            "目前缺什麼資料？",
            "資料來源是否明確？",
            "缺失資料是否會影響分類？",
            "是否需要人工確認後才回報？",
        ],
        "missing_required_fields": missing_fields,
        "missing_research_context": missing_context,
        "selected_skill_is_available": DEFAULT_REGISTRY[selected_skill]["status"] == "available",
    }


def _blocked_reason(skill_status: str, missing_fields: list[str]) -> str | None:
    if skill_status != "available":
        return "選中的 skill 尚未實作，不能執行。"
    if missing_fields:
        return f"資料不足，缺少必要欄位：{', '.join(missing_fields)}。"
    return None


def _format_plan_report(
    *,
    symbol: str,
    selected_skill: str,
    can_execute: bool,
    missing_fields: list[str],
    unknowns: dict[str, Any],
    steps: list[str],
) -> str:
    status = "可以執行" if can_execute else "暫停執行"
    missing = ", ".join(missing_fields) if missing_fields else "無"
    missing_context = ", ".join(unknowns["missing_research_context"]) or "無"
    step_text = "\n".join(f"- {step}" for step in steps)

    return (
        f"[Hermes Planner Gate] {symbol}\n"
        f"狀態：{status}\n"
        f"選擇 Skill：{selected_skill}\n\n"
        f"1. 任務理解\n"
        f"先確認資料是否足以呼叫 skill，再執行分析。\n\n"
        f"2. Unknown Discovery\n"
        f"缺少必要欄位：{missing}\n"
        f"缺少研究上下文：{missing_context}\n\n"
        f"3. 執行計畫\n"
        f"{step_text}\n\n"
        f"4. 安全邊界\n"
        f"只允許 read-only 分析、通知、記錄與人工確認；不下單、不預測必漲必跌。"
    )
