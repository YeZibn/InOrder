import pytest

from inorder_llm.context import HistoryConversation, OrderContext
from inorder_llm.graph.intent import build_intent_graph
from inorder_llm.graph.main import build_main_graph
from inorder_llm.graph.order import build_order_processing_graph
from inorder_llm.rewrite.models import RewriteResult


class IntentModel:
    def __init__(self, main, candidates=()):
        self.main = main
        self.candidates = list(candidates)
        self.calls = []

    def classify_main_intent(self, message):
        self.calls.append(("main", message))
        return {"main_intent": self.main, "confidence": 0.9}

    def extract_sub_intents(self, message, main_intent):
        self.calls.append(("sub", message, main_intent))
        return self.candidates


class Rewrite:
    def __init__(self): self.calls = []
    def rewrite(self, message, history, order_context):
        self.calls.append((message, history, order_context))
        return RewriteResult("新增一吨苹果", "新增一吨苹果")


class Extract:
    def __init__(self): self.calls = []
    def extract(self, message, reference_time):
        self.calls.append((message, reference_time))
        return []


def state():
    return {
        "message": "你好",
        "history": HistoryConversation(),
        "order_context": OrderContext(),
        "reference_time": "2026-08-24 10:00",
    }


def test_parent_routes_qa_without_order_subgraph():
    intent = IntentModel("qa")
    rewrite, extract = Rewrite(), Extract()
    graph = build_main_graph(build_intent_graph(intent), build_order_processing_graph(rewrite, extract))
    result = graph.invoke(state())
    assert result["main_intent"] == "qa"
    assert result["order_graph_entered"] is False
    assert result["order_result"] if "order_result" in result else True
    assert rewrite.calls == []
    assert extract.calls == []
    assert result["intent_result"]["intent_plan"].main_intent == "qa"


def test_parent_routes_order_and_passes_context_to_child():
    intent = IntentModel("order", [{"id": "step_1", "name": "create_order"}])
    rewrite, extract = Rewrite(), Extract()
    graph = build_main_graph(build_intent_graph(intent), build_order_processing_graph(rewrite, extract))
    result = graph.invoke({**state(), "message": "我要运货"})
    assert result["main_intent"] == "order"
    assert result["order_graph_entered"] is True
    assert result["order_result"]["rewrite_result"].extraction_text == "新增一吨苹果"
    assert rewrite.calls[0][0] == "我要运货"
    assert rewrite.calls[0][1] is not None
    assert rewrite.calls[0][2] is not None
    assert extract.calls == [("新增一吨苹果", "2026-08-24 10:00")]
    assert result["order_result"]["order_summary"].status == "incomplete"


def test_parent_propagates_child_errors():
    intent = IntentModel("order", [{"id": "step_1", "name": "create_order"}])
    class FailingRewrite:
        def rewrite(self, message, history, order_context):
            raise ValueError("rewrite failed")
    graph = build_main_graph(build_intent_graph(intent), build_order_processing_graph(FailingRewrite(), Extract()))
    with pytest.raises(ValueError, match="rewrite failed"):
        graph.invoke({**state(), "message": "我要运货"})
