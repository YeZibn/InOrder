from inorder_llm.graph.base import BaseGraph, BaseNode
from inorder_llm.graph.intent.graph import IntentGraph
from inorder_llm.graph.intent.state import IntentGraphState
from inorder_llm.graph.main import MainGraph, MainGraphState


def test_graph_structure_exports_base_abstractions():
    assert BaseNode.name == "node"
    assert hasattr(BaseGraph, "compile")
    assert IntentGraphState is not None
    assert hasattr(IntentGraph, "build")
    assert MainGraphState is not None
    assert hasattr(MainGraph, "build")
