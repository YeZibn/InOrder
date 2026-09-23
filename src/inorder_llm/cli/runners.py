"""Adapters that expose the three CLI execution chains."""

from dataclasses import dataclass
from typing import Protocol

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
    def __init__(self, main_graph):
        self.main_graph = main_graph

    def run(self, message: str, context: ChainContext) -> dict:
        result = dict(self.main_graph.invoke({
            "message": message,
            "history": context.history,
            "order_context": context.order_context,
            "reference_time": context.reference_time,
        }))
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
        result["intent_result"] = result.get("intent_result", {})
        return result


__all__ = ["ChainContext", "IntentChainRunner", "OrderChainRunner", "FullChainRunner"]
