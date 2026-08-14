from langgraph.graph import END, START, StateGraph

from ...graph.base import BaseGraph
from ...intent.protocols import IntentModel
from .nodes import BuildPlanNode, FinalizeNode, MainIntentNode, SubIntentNode, ValidatePlanNode
from .routing import route_main_intent
from .state import IntentGraphState


class IntentGraph(BaseGraph[IntentGraphState]):
    def __init__(self, model: IntentModel):
        self.model = model

    def build(self):
        builder = StateGraph(IntentGraphState)
        builder.add_node("main_intent", MainIntentNode(self.model))
        builder.add_node("sub_intent", SubIntentNode(self.model))
        builder.add_node("build_plan", BuildPlanNode())
        builder.add_node("validate_plan", ValidatePlanNode())
        builder.add_node("finalize", FinalizeNode())
        builder.add_edge(START, "main_intent")
        builder.add_conditional_edges("main_intent", route_main_intent, {"order": "sub_intent", "qa": "build_plan"})
        builder.add_edge("sub_intent", "build_plan")
        builder.add_edge("build_plan", "validate_plan")
        builder.add_edge("validate_plan", "finalize")
        builder.add_edge("finalize", END)
        return builder


def build_intent_graph(model: IntentModel):
    return IntentGraph(model).compile()
