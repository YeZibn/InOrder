"""LangGraph builder for order semantic parsing."""

from langgraph.graph import END, START, StateGraph

from ...graph.base import BaseGraph
from .nodes import ClarificationNode, ExtractNode, FinalizeNode, RewriteNode, route_rewrite
from .protocols import EntityExtractorModel, RewriteModel
from .state import OrderGraphState


class OrderProcessingGraph(BaseGraph[OrderGraphState]):
    def __init__(self, rewrite_model: RewriteModel, extractor: EntityExtractorModel):
        self.rewrite_model = rewrite_model
        self.extractor = extractor

    def build(self):
        builder = StateGraph(OrderGraphState)
        builder.add_node("rewrite", RewriteNode(self.rewrite_model))
        builder.add_node("extract", ExtractNode(self.extractor))
        builder.add_node("clarification", ClarificationNode())
        builder.add_node("finalize", FinalizeNode())
        builder.add_edge(START, "rewrite")
        builder.add_conditional_edges(
            "rewrite",
            route_rewrite,
            {"clarification": "clarification", "extract": "extract"},
        )
        builder.add_edge("clarification", "finalize")
        builder.add_edge("extract", "finalize")
        builder.add_edge("finalize", END)
        return builder


def build_order_processing_graph(
    rewrite_model: RewriteModel, extractor: EntityExtractorModel
):
    """Build and compile the standalone order-processing graph."""

    return OrderProcessingGraph(rewrite_model, extractor).compile()


__all__ = ["OrderProcessingGraph", "build_order_processing_graph"]
