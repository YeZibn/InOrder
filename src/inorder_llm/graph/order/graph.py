"""LangGraph builder for order semantic parsing."""

from langgraph.graph import END, START, StateGraph

from ...graph.base import BaseGraph
from .nodes import CargoProfileNode, ContextUpdateNode, ExtractNode, FinalizeNode, OrderCompletenessNode, RewriteNode, VehicleResolutionNode
from .protocols import CargoProfileModel, EntityExtractorModel, RewriteModel, VehicleResolutionModel
from .state import OrderGraphState


class OrderProcessingGraph(BaseGraph[OrderGraphState]):
    def __init__(self, rewrite_model: RewriteModel, extractor: EntityExtractorModel, profile_model: CargoProfileModel | None = None, vehicle_model: VehicleResolutionModel | None = None):
        self.rewrite_model = rewrite_model
        self.extractor = extractor
        self.profile_model = profile_model
        self.vehicle_model = vehicle_model

    def build(self):
        builder = StateGraph(OrderGraphState)
        builder.add_node("rewrite", RewriteNode(self.rewrite_model))
        builder.add_node("extract", ExtractNode(self.extractor))
        builder.add_node("update_context", ContextUpdateNode())
        if self.profile_model is not None:
            builder.add_node("cargo_profile", CargoProfileNode(self.profile_model))
        if self.vehicle_model is not None:
            builder.add_node("vehicle_resolution", VehicleResolutionNode(self.vehicle_model))
        builder.add_node("order_completeness", OrderCompletenessNode())
        builder.add_node("finalize", FinalizeNode())
        builder.add_edge(START, "rewrite")
        builder.add_edge("rewrite", "extract")
        builder.add_edge("extract", "update_context")
        if self.profile_model is not None and self.vehicle_model is not None:
            builder.add_conditional_edges(
                "update_context",
                lambda state: "cargo_profile" if state.get("cargo_updated") else "vehicle_resolution",
                {"cargo_profile": "cargo_profile", "vehicle_resolution": "vehicle_resolution"},
            )
            builder.add_edge("cargo_profile", "vehicle_resolution")
            builder.add_edge("vehicle_resolution", "order_completeness")
        elif self.profile_model is not None:
            builder.add_conditional_edges(
                "update_context",
                lambda state: "cargo_profile" if state.get("cargo_updated") else "order_completeness",
                {"cargo_profile": "cargo_profile", "order_completeness": "order_completeness"},
            )
            builder.add_edge("cargo_profile", "order_completeness")
        elif self.vehicle_model is not None:
            builder.add_edge("update_context", "vehicle_resolution")
            builder.add_edge("vehicle_resolution", "order_completeness")
        else:
            builder.add_edge("update_context", "order_completeness")
        builder.add_edge("order_completeness", "finalize")
        builder.add_edge("finalize", END)
        return builder


def build_order_processing_graph(
    rewrite_model: RewriteModel, extractor: EntityExtractorModel, profile_model: CargoProfileModel | None = None, vehicle_model: VehicleResolutionModel | None = None
):
    """Build and compile the standalone order-processing graph."""

    return OrderProcessingGraph(rewrite_model, extractor, profile_model, vehicle_model).compile()


__all__ = ["OrderProcessingGraph", "build_order_processing_graph"]
