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

def test_compiled_graph_order_executes_only_main_intent():
    model = RecordingModel("order")
    result = build_intent_graph(model).invoke({"message": "修改当前草稿"})
    assert model.calls == ["main_intent_node"]
    assert result["main_intent"] == "order"
    assert "sub_intents" not in result


def test_qa_route_skips_sub_intent_node_and_has_unified_output():
    model = RecordingModel("qa")
    result = build_intent_graph(model).invoke({"message": "什么是预约配送"})
    assert model.calls == ["main_intent_node"]
    assert result["main_intent"] == "qa"
    assert "sub_intents" not in result


def test_order_without_sub_intent_still_routes_order():
    model = RecordingModel("order")
    result = build_intent_graph(model).invoke({"message": "帮我处理一下"})
    assert model.calls == ["main_intent_node"]
    assert result["main_intent"] == "order"
    assert "needs_clarification" not in result


def test_business_goal_message_routes_to_order():
    model = RecordingModel("order")
    result = build_intent_graph(model).invoke({"message": "我想从上海运货到温州"})
    assert result["main_intent"] == "order"
    assert model.messages == ["我想从上海运货到温州"]
    assert "needs_clarification" not in result


def test_capability_inquiry_message_routes_to_qa():
    model = RecordingModel("qa")
    result = build_intent_graph(model).invoke({"message": "上海到温州能运吗"})
    assert result["main_intent"] == "qa"
    assert model.messages == ["上海到温州能运吗"]
    assert "sub_intents" not in result


def test_graph_is_recognition_only():
    model = RecordingModel("order")
    result = build_intent_graph(model).invoke({"message": "创建订单"})
    assert "sub_intents" not in result
    assert not hasattr(model, "query_history")
    assert not hasattr(model, "modify_draft")
