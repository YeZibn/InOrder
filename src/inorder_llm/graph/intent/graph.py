from langgraph.graph import END, START, StateGraph

from ...graph.base import BaseGraph
from ...graph.runnable import dual_node
from ...intent.protocols import IntentModel
from .nodes import FinalizeNode, MainIntentNode
from .routing import route_main_intent
from .state import IntentGraphState


class IntentGraph(BaseGraph[IntentGraphState]):
    def __init__(self, model: IntentModel, executor=None):
        self.model = model
        self.executor = executor

    def build(self):
        builder = StateGraph(IntentGraphState)
        builder.add_node("main_intent", dual_node(MainIntentNode(self.model), self.executor))
        builder.add_node("finalize", dual_node(FinalizeNode(), self.executor))
        builder.add_edge(START, "main_intent")
        builder.add_edge("main_intent", "finalize")
        builder.add_edge("finalize", END)
        return builder


def build_intent_graph(model: IntentModel, executor=None):
    return IntentGraph(model, executor).compile()
