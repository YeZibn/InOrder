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
        result.update(
            {
                "order_graph_entered": True,
                "rewrite_completed": rewrite_result is not None,
                "extract_executed": True,
                "entity_count": len(result.get("entities", ())),
                "order_context_updated": bool(result.get("order_context_updated")),
                "cargo_profile_updated": bool(result.get("cargo_profile_updated")),
                "vehicle_resolution_completed": result.get("vehicle_resolution") is not None,
            }
        )
        return result


class FullChainRunner:
    def __init__(self, intent_runner: IntentChainRunner, order_runner: Optional[OrderChainRunner] = None, main_graph=None):
        self.intent_runner = intent_runner
        self.order_runner = order_runner
        self.main_graph = main_graph

    def run(self, message: str, context: ChainContext) -> dict:
        if self.main_graph is not None:
            result = dict(self.main_graph.invoke({
                "message": message,
                "history": context.history,
                "order_context": context.order_context,
                "reference_time": context.reference_time,
            }))
            intent_result = result.get("intent_result", {})
            order_result = result.get("order_result")
            if order_result is not None:
                order_result = dict(order_result)
                order_result.setdefault("order_graph_entered", True)
                order_result.setdefault("rewrite_completed", order_result.get("rewrite_result") is not None)
                order_result.setdefault("extract_executed", True)
                order_result.setdefault("entity_count", len(order_result.get("entities", ())))
                order_result.setdefault("order_context_updated", bool(order_result.get("order_context_updated")))
                order_result.setdefault("cargo_profile_updated", bool(order_result.get("cargo_profile_updated")))
                result["order_result"] = order_result
            result["intent_result"] = intent_result
            return result
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
