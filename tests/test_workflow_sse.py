import json

from fastapi.testclient import TestClient

from inorder_llm.context import HistoryConversation, OrderContext
from inorder_llm.workflow import EventType, WorkflowEvent, WorkflowEventAdapter, error_event
from inorder_llm.workflow.api import create_app


class FakeGraph:
    def __init__(self, result=None, error=None):
        self.result = result or {"intent_result": {"main_intent": "qa"}, "order_graph_entered": False}
        self.error = error

    def invoke(self, state):
        if self.error:
            raise self.error
        return self.result


class StreamingGraph(FakeGraph):
    def stream(self, state, stream_mode="updates"):
        assert stream_mode == "updates"
        yield {"intent_subgraph": {"main_intent": "order"}}
        yield {"order_subgraph": {"rewrite_result": {"rewritten_text": "x"}}}
        yield {"rewrite": {"rewrite_result": {"rewritten_text": "x"}}}
        yield {"extract": {"entities": []}}
        yield {"update_context": {"order_context_updated": True}}
        yield {"cargo_profile": {"cargo_profile_updated": True}}
        yield {"vehicle_resolution": {"vehicle_resolution": {"vehicle_type": "厢式"}}}


def frames(text):
    return [json.loads(line[6:]) for line in text.splitlines() if line.startswith("data: ")]


def test_event_frame_and_error_are_safe():
    event = WorkflowEvent(EventType.THINKING_STEP, {"title": "识别", "prompt": "secret"})
    body = json.loads(event.frame()[6:])
    assert body["type"] == "THINKING_STEP"
    assert error_event(RuntimeError("prompt=secret stack"), "extract").to_dict()["payload"] == {
        "code": "WORKFLOW_ERROR", "message": "工作流处理失败", "stage": "extract"
    }


def test_adapter_qa_has_terminal_lifecycle_without_context():
    events = list(WorkflowEventAdapter(FakeGraph()).events({"session_id": "s"}))
    assert [event.type for event in events] == [EventType.THINKING_START, EventType.THINKING_STEP, EventType.THINKING_DONE, EventType.DONE]
    assert all(event.type != EventType.CREATE_ORDER_CONTEXT for event in events)


def test_adapter_order_emits_context_only_when_updated():
    context = OrderContext(cargo=[{"name": "苹果"}])
    result = {"intent_result": {"main_intent": "order"}, "order_graph_entered": True,
              "order_result": {"rewrite_result": {"rewritten_text": "x"}, "entities": [],
                               "order_context": context, "order_context_updated": True}}
    events = list(WorkflowEventAdapter(FakeGraph(result)).events({"session_id": "s"}))
    kinds = [event.type for event in events]
    assert EventType.CREATE_ORDER_CONTEXT in kinds
    assert kinds[-2:] == [EventType.THINKING_DONE, EventType.DONE]


def test_adapter_exposes_only_business_stages_for_streaming_graph():
    events = list(WorkflowEventAdapter(StreamingGraph({
        "intent_result": {"main_intent": "order"},
        "order_graph_entered": True,
        "order_result": {"order_context_updated": False},
    })).events({"session_id": "s"}))
    steps = [event.payload for event in events if event.type == EventType.THINKING_STEP]
    assert [step["stage"] for step in steps] == ["intent", "order", "cargo_profile", "vehicle"]
    assert [step["title"] for step in steps] == ["识别用户意图", "处理订单", "生成货物画像", "处理车型"]
    assert all(step["stage"] in {"intent", "order", "cargo_profile", "vehicle"} for step in steps)


def test_api_valid_request_and_validation_error():
    client = TestClient(create_app(main_graph=FakeGraph()))
    response = client.post("/api/v2/chat", json={"session_id": "s", "message": "你好"})
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    assert [item["type"] for item in frames(response.text)][-1] == "DONE"
    bad = client.post("/api/v2/chat", json={"session_id": "s", "message": " "})
    assert bad.status_code == 422


def test_api_error_is_terminal_without_done():
    client = TestClient(create_app(main_graph=FakeGraph(error=RuntimeError("secret"))))
    items = frames(client.post("/api/v2/chat", json={"session_id": "s", "message": "你好"}).text)
    assert items[-1]["type"] == "ERROR"
    assert all(item["type"] != "DONE" for item in items)
