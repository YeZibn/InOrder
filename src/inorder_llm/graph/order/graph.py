"""LangGraph builder for order semantic parsing."""

from langgraph.graph import END, START, StateGraph

from ...graph.base import BaseGraph
from .nodes import CargoProfileNode, ContextUpdateNode, ExtractNode, FinalizeNode, RewriteNode
from .protocols import CargoProfileModel, EntityExtractorModel, RewriteModel
from .state import OrderGraphState


class OrderProcessingGraph(BaseGraph[OrderGraphState]):
    def __init__(self, rewrite_model: RewriteModel, extractor: EntityExtractorModel, profile_model: CargoProfileModel | None = None):
        self.rewrite_model = rewrite_model
        self.extractor = extractor
        self.profile_model = profile_model

    def build(self):
        builder = StateGraph(OrderGraphState)
        builder.add_node("rewrite", RewriteNode(self.rewrite_model))
        builder.add_node("extract", ExtractNode(self.extractor))
        builder.add_node("update_context", ContextUpdateNode())
        if self.profile_model is not None:
            builder.add_node("cargo_profile", CargoProfileNode(self.profile_model))
        builder.add_node("finalize", FinalizeNode())
        builder.add_edge(START, "rewrite")
        builder.add_edge("rewrite", "extract")
        builder.add_edge("extract", "update_context")
        if self.profile_model is not None:
            builder.add_conditional_edges(
                "update_context",
                lambda state: "cargo_profile" if state.get("cargo_updated") else "finalize",
                {"cargo_profile": "cargo_profile", "finalize": "finalize"},
            )
            builder.add_edge("cargo_profile", "finalize")
        else:
            builder.add_edge("update_context", "finalize")
        builder.add_edge("finalize", END)
        return builder


def build_order_processing_graph(
    rewrite_model: RewriteModel, extractor: EntityExtractorModel, profile_model: CargoProfileModel | None = None
):
    """Build and compile the standalone order-processing graph."""

    return OrderProcessingGraph(rewrite_model, extractor, profile_model).compile()


__all__ = ["OrderProcessingGraph", "build_order_processing_graph"]
