"""Shared extraction of assistant history summaries from structured results.

CLI and API previously kept parallel implementations that drifted apart; both
entry points now consume this module as the single source for dict conversion
and assistant summary extraction.
"""

from typing import Any, Dict, Tuple


def to_data(value):
    """Return a JSON-compatible view for domain objects exposing ``to_dict``."""
    return value.to_dict() if hasattr(value, "to_dict") else value


def intent_view(result):
    """Intent result view, unwrapping dataclass intent plans."""
    plan = result.get("intent_plan") if isinstance(result, dict) else None
    return to_data(plan) if plan is not None else result


def order_summary_view(result) -> Dict[str, Any] | None:
    """Order summary view from either the nested ``order_result`` or top level."""
    source = result.get("order_result") or result
    summary = to_data(source.get("order_summary")) if isinstance(source, dict) else None
    return summary if isinstance(summary, dict) and (summary.get("user_message") or summary.get("summary")) else None


def summarize_assistant(result) -> Tuple[str, Dict[str, Any]]:
    """Extract ``(text, metadata)`` following a fixed fallback order.

    1. ``order_summary.user_message`` / ``summary`` — 订单最终总结。
    2. 意图摘要素材（main_intent）。
    3. 简短兜底文案。

    Metadata carries business facts only; callers add entry-point specific
    fields such as ``chain`` or ``recovered``.
    """
    if isinstance(result, str):
        return result, {}
    summary = order_summary_view(result)
    if summary is not None:
        text = summary.get("user_message") or summary.get("summary", "")
        intent = None
        intent_result = result.get("intent_result")
        if isinstance(intent_result, dict):
            intent = intent_view(intent_result).get("main_intent")
        return str(text), {"main_intent": intent, "order_status": summary.get("status", "incomplete")}
    intent_source = result.get("intent_result")
    data = intent_view(intent_source) if isinstance(intent_source, dict) else intent_view(result)
    intent = data.get("main_intent") if isinstance(data, dict) else None
    if intent is None:
        return "已完成意图识别：未知", {}
    return f"已完成意图识别：{intent}", {"main_intent": intent}


__all__ = ["to_data", "intent_view", "order_summary_view", "summarize_assistant"]
