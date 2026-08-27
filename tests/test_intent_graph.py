from inorder_llm.graph.intent import build_intent_graph


class RecordingModel:
    def __init__(self, main, candidates=()):
        self.main = main
        self.candidates = list(candidates)
        self.calls = []
        self.messages = []

    def classify_main_intent(self, message):
        self.calls.append("main_intent_node")
        self.messages.append(message)
        return {"main_intent": self.main, "confidence": 0.9}

    def extract_sub_intents(self, message, main_intent):
        self.calls.append("sub_intent_node")
        return self.candidates


def test_compiled_graph_order_executes_both_intent_nodes():
    model = RecordingModel("order", [{"id": "draft", "name": "modify_draft"}])
    result = build_intent_graph(model).invoke({"message": "修改当前草稿"})
    assert model.calls == ["main_intent_node", "sub_intent_node"]
    assert result["main_intent"] == "order"
    assert [s.name for s in result["intent_plan"].sub_intents] == ["modify_draft"]
    assert result["needs_clarification"] is False


def test_qa_route_skips_sub_intent_node_and_has_unified_output():
    model = RecordingModel("qa")
    result = build_intent_graph(model).invoke({"message": "什么是预约配送"})
    assert model.calls == ["main_intent_node"]
    assert result["main_intent"] == "qa"
    assert result["intent_plan"].sub_intents == ()
    assert result["needs_clarification"] is False


def test_order_without_sub_intent_needs_clarification():
    model = RecordingModel("order")
    result = build_intent_graph(model).invoke({"message": "帮我处理一下"})
    assert model.calls == ["main_intent_node", "sub_intent_node"]
    assert result["main_intent"] == "order"
    assert result["needs_clarification"] is True
    assert result["clarification_reason"]
    assert result["intent_plan"].sub_intents == ()


def test_business_goal_message_routes_to_order():
    model = RecordingModel("order", [{"id": "s1", "name": "create_order"}])
    result = build_intent_graph(model).invoke({"message": "我想从上海运货到温州"})
    assert result["main_intent"] == "order"
    assert model.messages == ["我想从上海运货到温州"]
    assert result["needs_clarification"] is False


def test_capability_inquiry_message_routes_to_qa():
    model = RecordingModel("qa")
    result = build_intent_graph(model).invoke({"message": "上海到温州能运吗"})
    assert result["main_intent"] == "qa"
    assert model.messages == ["上海到温州能运吗"]
    assert result["intent_plan"].sub_intents == ()


def test_graph_is_recognition_only():
    model = RecordingModel("order", [{"name": "create_order"}])
    result = build_intent_graph(model).invoke({"message": "创建订单"})
    assert result["intent_plan"].sub_intents[0].name == "create_order"
    assert not hasattr(model, "query_history")
    assert not hasattr(model, "modify_draft")
