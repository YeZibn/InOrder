"""Adapters that expose the three CLI execution chains."""

from dataclasses import dataclass
from typing import Optional, Protocol

from ..context.models import HistoryConversation, OrderContext


class GraphLike(Protocol):
    def invoke(self, state: dict) -> dict: ...


@dataclass
class ChainContext:
    history: HistoryConversation
    order_context: OrderContext
    reference_time: str


class IntentChainRunner:
    def __init__(self, graph: GraphLike):
        self.graph = graph

    def run(self, message: str, context: ChainContext) -> dict:
        return self.graph.invoke({"message": message})


class OrderChainRunner:
    def __init__(self, graph: GraphLike):
        self.graph = graph

    def run(self, message: str, context: ChainContext) -> dict:
        raw_result = self.graph.invoke(
            {
                "message": message,
                "history": context.history,
                "order_context": context.order_context,
                "reference_time": context.reference_time,
            }
        )
        result = dict(raw_result)
        rewrite_result = result.get("rewrite_result")
        needs_clarification = bool(result.get("needs_clarification"))
        result.update(
            {
                "order_graph_entered": True,
                "rewrite_completed": rewrite_result is not None,
                "extract_executed": not needs_clarification,
                "extract_skipped_reason": (
                    result.get("clarification_reason") if needs_clarification else None
                ),
                "entity_count": len(result.get("entities", ())),
                "order_context_updated": bool(result.get("order_context_updated")),
                "cargo_profile_updated": bool(result.get("cargo_profile_updated")),
            }
        )
        return result


class FullChainRunner:
    def __init__(self, intent_runner: IntentChainRunner, order_runner: Optional[OrderChainRunner] = None):
        self.intent_runner = intent_runner
        self.order_runner = order_runner

    def run(self, message: str, context: ChainContext) -> dict:
        intent_result = self.intent_runner.run(message, context)
        plan = intent_result.get("intent_plan")
        main_intent = intent_result.get("main_intent")
        if plan is not None:
            main_intent = getattr(plan, "main_intent", None) or plan.get("main_intent")
        result = {"intent_result": intent_result}
        if main_intent == "order" and self.order_runner is not None:
            result["order_result"] = self.order_runner.run(message, context)
        elif main_intent == "order":
            result.update(
                {
                    "order_graph_entered": False,
                    "rewrite_completed": False,
                    "extract_executed": False,
                    "extract_skipped_reason": "订单处理子图未配置",
                    "entity_count": 0,
                }
            )
        elif main_intent == "qa":
            result["qa_placeholder"] = "问答入口尚未实现（当前仅支持识别与订单语义解析）。"
        return result


__all__ = ["ChainContext", "IntentChainRunner", "OrderChainRunner", "FullChainRunner"]
