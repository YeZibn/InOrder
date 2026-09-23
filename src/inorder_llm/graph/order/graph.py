"""LangGraph builder for order semantic parsing."""

from langgraph.graph import END, START, StateGraph

from ...graph.base import BaseGraph
from ...graph.runnable import dual_node
from .nodes import CargoProfileNode, ContextUpdateNode, ExtractNode, FinalizeNode, OrderCompletenessNode, RewriteNode, VehicleResolutionNode
from .protocols import CargoProfileModel, EntityExtractorModel, RewriteModel, VehicleResolutionModel
from .state import OrderGraphState


class OrderProcessingGraph(BaseGraph[OrderGraphState]):
    def __init__(self, rewrite_model: RewriteModel, extractor: EntityExtractorModel, profile_model: CargoProfileModel | None = None, vehicle_model: VehicleResolutionModel | None = None, executor=None, extract_executor=None, extract_llm_gate=None):
        self.rewrite_model = rewrite_model
        self.extractor = extractor
        self.profile_model = profile_model
        self.vehicle_model = vehicle_model
        self.executor = executor
        self.extract_executor = extract_executor or executor
        self.extract_llm_gate = extract_llm_gate

    def build(self):
        builder = StateGraph(OrderGraphState)
        builder.add_node("rewrite", dual_node(RewriteNode(self.rewrite_model), self.executor))
        builder.add_node("extract", dual_node(ExtractNode(self.extractor), self.extract_executor, self.extract_llm_gate))
        builder.add_node("update_context", dual_node(ContextUpdateNode(), self.executor))
        if self.profile_model is not None:
            builder.add_node("cargo_profile", dual_node(CargoProfileNode(self.profile_model), self.executor))
        if self.vehicle_model is not None:
            builder.add_node("vehicle_resolution", dual_node(VehicleResolutionNode(self.vehicle_model), self.executor))
        builder.add_node("order_completeness", dual_node(OrderCompletenessNode(), self.executor))
        builder.add_node("finalize", dual_node(FinalizeNode(), self.executor))
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
    rewrite_model: RewriteModel, extractor: EntityExtractorModel, profile_model: CargoProfileModel | None = None, vehicle_model: VehicleResolutionModel | None = None, executor=None, extract_executor=None, extract_llm_gate=None
):
    """Build and compile the standalone order-processing graph."""

    return OrderProcessingGraph(rewrite_model, extractor, profile_model, vehicle_model, executor, extract_executor, extract_llm_gate).compile()


__all__ = ["OrderProcessingGraph", "build_order_processing_graph"]
