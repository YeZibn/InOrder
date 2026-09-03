from langgraph.graph import END, START, StateGraph

from ...graph.base import BaseGraph
from ...intent.protocols import IntentModel
from .nodes import FinalizeNode, MainIntentNode
from .routing import route_main_intent
from .state import IntentGraphState


class IntentGraph(BaseGraph[IntentGraphState]):
    def __init__(self, model: IntentModel):
        self.model = model

    def build(self):
        builder = StateGraph(IntentGraphState)
        builder.add_node("main_intent", MainIntentNode(self.model))
        builder.add_node("finalize", FinalizeNode())
        builder.add_edge(START, "main_intent")
        builder.add_edge("main_intent", "finalize")
        builder.add_edge("finalize", END)
        return builder


def build_intent_graph(model: IntentModel):
    return IntentGraph(model).compile()
