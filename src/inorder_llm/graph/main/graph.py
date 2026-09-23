"""LangGraph parent workflow that composes intent and order subgraphs."""

from typing import Any, Mapping

from langgraph.graph import END, START, StateGraph

from ..base import BaseGraph
from ..runnable import dual_node
from ..intent.graph import build_intent_graph
from ..order.graph import build_order_processing_graph
from ...extract.langextract_adapter import LangExtractEntityExtractor
from .routing import route_main_graph
from .state import MainGraphState


def _as_dict(value: Any) -> dict:
    if isinstance(value, dict):
        return dict(value)
    if hasattr(value, "to_dict"):
        return value.to_dict()
    return {}


class MainGraph(BaseGraph[MainGraphState]):
    def __init__(self, intent_graph, order_graph, executor=None):
        self.intent_graph = intent_graph
        self.order_graph = order_graph
        self.executor = executor

    def build(self):
        builder = StateGraph(MainGraphState)
        builder.add_node("intent_subgraph", self.intent_graph)
        builder.add_node("order_subgraph", self.order_graph)
        builder.add_node("mark_order_entered", dual_node(self._mark_order_entered, self.executor))
        builder.add_node("qa_terminal", dual_node(self._qa_terminal, self.executor))
        builder.add_node("finalize", dual_node(self._finalize, self.executor))
        builder.add_edge(START, "intent_subgraph")
        builder.add_conditional_edges(
            "intent_subgraph",
            route_main_graph,
            {"order": "order_subgraph", "qa": "qa_terminal"},
        )
        builder.add_edge("order_subgraph", "mark_order_entered")
        builder.add_edge("mark_order_entered", "finalize")
        builder.add_edge("qa_terminal", "finalize")
        builder.add_edge("finalize", END)
        return builder

    @staticmethod
    def _mark_order_entered(state: MainGraphState) -> Mapping[str, Any]:
        return {"order_graph_entered": True}

    @staticmethod
    def _qa_terminal(state: MainGraphState) -> Mapping[str, Any]:
        return {
            "qa_placeholder": "问答入口尚未实现（当前仅支持识别与订单语义解析）。",
            "order_graph_entered": False,
            "rewrite_completed": False,
            "extract_executed": False,
            "entity_count": 0,
        }

    @staticmethod
    def _finalize(state: MainGraphState) -> Mapping[str, Any]:
        intent_data = {
            key: state[key]
            for key in ("main_intent", "main_confidence")
            if key in state
        }
        order_keys = (
            "rewrite_result", "entities", "order_context", "order_context_updated",
            "cargo_profile_updated", "vehicle_resolution",
            "order_summary",
        )
        order_data = {key: state[key] for key in order_keys if key in state}
        if state.get("order_graph_entered"):
            order_data.update({
                "order_graph_entered": True,
                "rewrite_completed": state.get("rewrite_result") is not None,
                "extract_executed": True,
                "entity_count": len(state.get("entities", ())),
            })
        result = dict(state)
        result["intent_result"] = intent_data
        if state.get("order_graph_entered"):
            result["order_result"] = order_data
        result.setdefault("order_graph_entered", False)
        return result


def build_main_graph(intent_graph, order_graph, executor=None):
    """Compile a parent graph from already-built intent and order subgraphs."""
    return MainGraph(intent_graph, order_graph, executor).compile()


def build_main_graph_from_models(intent_model, rewrite_model, extractor, profile_model=None, vehicle_model=None, capacity=None):
    executor = capacity.sync_nodes if capacity is not None else None
    extract_executor = capacity.langextract if capacity is not None and isinstance(extractor, LangExtractEntityExtractor) else executor
    return build_main_graph(
        build_intent_graph(intent_model, executor),
        build_order_processing_graph(rewrite_model, extractor, profile_model, vehicle_model, executor, extract_executor, capacity.llm if capacity is not None and isinstance(extractor, LangExtractEntityExtractor) else None),
        executor,
    )


__all__ = ["MainGraph", "build_main_graph", "build_main_graph_from_models"]
