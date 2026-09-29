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


def _order_result_with_metadata(raw_result: dict) -> dict:
    result = dict(raw_result)
    result.setdefault("order_graph_entered", True)
    result.setdefault("rewrite_completed", result.get("rewrite_result") is not None)
    result.setdefault("extract_executed", True)
    result.setdefault("entity_count", len(result.get("entities", ())))
    result.setdefault("order_context_updated", bool(result.get("order_context_updated")))
    result.setdefault("cargo_profile_updated", bool(result.get("cargo_profile_updated")))
    result.setdefault("vehicle_resolution_completed", result.get("vehicle_resolution") is not None)
    return result


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
        return {"order_result": _order_result_with_metadata(raw_result)}


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
        result.pop("order_context", None)
        order_result = result.get("order_result")
        if order_result is not None:
            result["order_result"] = _order_result_with_metadata(order_result)
        result["intent_result"] = result.get("intent_result", {})
        return result


__all__ = ["ChainContext", "IntentChainRunner", "OrderChainRunner", "FullChainRunner"]
