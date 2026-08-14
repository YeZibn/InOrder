from inorder_llm.intent_graph import build_intent_graph


class RecordingModel:
    def __init__(self, main, candidates=()):
        self.main = main
        self.candidates = list(candidates)
        self.calls = []

    def classify_main_intent(self, message):
        self.calls.append("main_intent_node")
        return {"main_intent": self.main, "confidence": 0.9}

    def extract_sub_intents(self, message, main_intent):
        self.calls.append("sub_intent_node")
        return self.candidates


def test_compiled_graph_order_executes_both_intent_nodes():
    model = RecordingModel("order", [
        {"id": "history", "name": "query_history_order"},
        {"id": "draft", "name": "modify_draft", "depends_on": ["history"]},
    ])
    result = build_intent_graph(model).invoke({"message": "参考历史订单修改当前草稿"})
    assert model.calls == ["main_intent_node", "sub_intent_node"]
    assert result["main_intent"] == "order"
    assert [s.name for s in result["intent_plan"].sub_intents] == ["query_history_order", "modify_draft"]


def test_qa_route_skips_sub_intent_node_and_has_unified_output():
    model = RecordingModel("qa")
    result = build_intent_graph(model).invoke({"message": "什么是预约配送"})
    assert model.calls == ["main_intent_node"]
    assert result["main_intent"] == "qa"
    assert result["intent_plan"].sub_intents == ()
    assert result["needs_clarification"] is False


def test_ambiguous_route_enters_clarification_without_sub_intent():
    model = RecordingModel("ambiguous", [{"name": "create_order"}])
    result = build_intent_graph(model).invoke({"message": "查一下并告诉我怎么下单"})
    assert model.calls == ["main_intent_node"]
    assert result["needs_clarification"] is True
    assert result["clarification_reason"]
    assert result["intent_plan"].main_intent == "ambiguous"


def test_graph_is_recognition_only():
    model = RecordingModel("order", [{"name": "query_history_order"}])
    result = build_intent_graph(model).invoke({"message": "查询历史订单"})
    assert result["intent_plan"].sub_intents[0].name == "query_history_order"
    assert not hasattr(model, "query_history")
    assert not hasattr(model, "modify_draft")
