import json
from pathlib import Path

from fastapi.testclient import TestClient

from inorder_llm.context import HistoryConversation, OrderContext
from inorder_llm.workflow import EventType, WorkflowEvent, WorkflowEventAdapter, error_event
from inorder_llm.workflow.api import create_app
from inorder_llm.infrastructure.llm.errors import WorkflowTimeoutError


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


class NestedStreamingGraph(FakeGraph):
    def stream(self, state, stream_mode="updates", subgraphs=False, version="v1"):
        assert stream_mode == "updates"
        assert subgraphs is True
        records = [
            (("intent_subgraph:run",), {"main_intent": {"main_intent": "order"}}),
            (("order_subgraph:run",), {"rewrite": {"rewrite_result": {"rewritten_text": "x"}}}),
            (("order_subgraph:run",), {"extract": {"entities": []}}),
            (("order_subgraph:run",), {"update_context": {"order_context_updated": True}}),
            (("order_subgraph:run",), {"cargo_profile": {"cargo_profile_updated": True}}),
            (("order_subgraph:run",), {"vehicle_resolution": {"vehicle_resolution": {"vehicle_type": "厢式"}}}),
            ((), {"order_subgraph": {"order_graph_entered": True}}),
        ]
        for namespace, data in records:
            yield (namespace, data)


class NestedV2StreamingGraph(FakeGraph):
    def stream(self, state, stream_mode="updates", subgraphs=False, version="v2"):
        assert subgraphs is True
        yield {"type": "updates", "ns": ["order_subgraph:run"], "data": {"rewrite": {"rewrite_result": {"rewritten_text": "x"}}}}
        yield {"type": "updates", "ns": ["order_subgraph:run"], "data": {"extract": {"entities": []}}}
        yield {"type": "updates", "ns": [], "data": {"order_subgraph": {"order_graph_entered": True}}}


def frames(text):
    return [json.loads(line[6:]) for line in text.splitlines() if line.startswith("data: ")]


def test_event_frame_and_error_are_safe():
    event = WorkflowEvent(EventType.THINKING_STEP, {"title": "识别", "prompt": "secret"})
    body = json.loads(event.frame()[6:])
    assert body["type"] == "THINKING_STEP"
    assert error_event(RuntimeError("prompt=secret stack"), "extract").to_dict()["payload"] == {
        "code": "WORKFLOW_ERROR", "message": "工作流处理失败", "stage": "extract", "retryable": False
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


def test_done_event_includes_order_summary_without_raw_dataclass_leak():
    context = OrderContext(
        pickup_location={"city": "温州"}, dropoff_location={"city": "上海"},
        cargo=[{"name": "苹果", "weight": ["1吨"]}],
        delivery_time={"start": "2026-08-28T10:00:00"},
    )
    result = {"intent_result": {"main_intent": "order"}, "order_graph_entered": True,
              "order_result": {"order_context": context, "order_context_updated": True,
                               "order_summary": {"status": "complete", "summary": "订单已准备好"}}}
    items = list(WorkflowEventAdapter(FakeGraph(result)).events({"session_id": "s"}))
    done = items[-1].to_dict()
    assert done["type"] == "DONE"
    assert done["payload"]["result"]["order_result"]["order_summary"]["status"] == "complete"


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


def test_adapter_emits_nested_child_node_completion_events_in_order():
    events = list(WorkflowEventAdapter(NestedStreamingGraph()).events({"session_id": "s"}))
    steps = [event.payload for event in events if event.type == EventType.THINKING_STEP]
    assert [step["node"] for step in steps] == ["main_intent", "rewrite", "extract", "update_context", "cargo_profile", "vehicle_resolution"]
    assert [step["sequence"] for step in steps] == list(range(1, 7))
    assert all(step["status"] == "completed" for step in steps)
    assert steps[1]["title"] == "订单语义整理完成"


def test_adapter_parses_v2_nested_updates_and_keeps_terminal_events():
    events = list(WorkflowEventAdapter(NestedV2StreamingGraph()).events({"session_id": "s"}))
    steps = [event.payload for event in events if event.type == EventType.THINKING_STEP and "node" in event.payload]
    assert [step["node"] for step in steps] == ["rewrite", "extract"]
    assert [event.type for event in events[-2:]] == [EventType.THINKING_DONE, EventType.DONE]


def test_api_valid_request_and_validation_error():
    client = TestClient(create_app(main_graph=FakeGraph()))
    response = client.post("/api/v2/chat", json={"session_id": "s", "message": "你好"})
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    assert [item["type"] for item in frames(response.text)][-1] == "DONE"
    bad = client.post("/api/v2/chat", json={"session_id": "s", "message": " "})
    assert bad.status_code == 422


def test_api_done_returns_recovered_history_for_pending_user():
    graph = FakeGraph({"intent_result": {"main_intent": "qa"}, "order_graph_entered": False})
    client = TestClient(create_app(main_graph=graph))
    response = client.post("/api/v2/chat", json={
        "session_id": "s", "message": "从温州到上海",
        "history": {"turns": [{"role": "user", "content": "我要运苹果"}]},
    })
    done = frames(response.text)[-1]
    assert done["type"] == "DONE"
    assert done["payload"]["history_recovered"] is True
    turns = done["payload"]["history"]["turns"]
    assert turns[-2]["role"] == "user"
    assert turns[-2]["content"] == "我要运苹果\n从温州到上海"
    assert turns[-1]["role"] == "assistant"


def test_api_serves_same_origin_memory_test_page():
    client = TestClient(create_app(main_graph=FakeGraph()))
    response = client.get("/")
    assert response.status_code == 200
    assert "InOrder" in response.text
    assert "api/v2/chat" in response.text


def test_memory_page_maps_sse_events_to_friendly_progress_hints():
    page = (Path(__file__).parents[1] / "frontend" / "index.html").read_text(encoding="utf-8")
    # The browser owns this presentation mapping; backend event names must not
    # be rendered as the user-facing progress text.
    for hint in (
        "正在理解您的需求…",
        "正在识别您的运输需求…",
        "正在整理订单信息…",
        "正在分析货物特征…",
        "正在匹配合适车型…",
        "订单信息已更新",
        "处理完成",
    ):
        assert hint in page
    assert "const STAGE_HINTS" in page
    assert "const friendlyHint" in page
    assert "const createProgressBubble" in page
    assert "正在处理您的订单…" in page
    assert "normalizeStage(payload.stage)" in page
    assert "|| 'unknown'" in page


def test_memory_page_maps_node_events_and_appends_same_stage_progress():
    page = (Path(__file__).parents[1] / "frontend" / "index.html").read_text(encoding="utf-8")
    for hint in ("主意图识别完成", "订单语义整理完成", "订单字段提取完成", "订单信息检查完成"):
        assert hint in page
    assert "const NODE_HINTS" in page
    assert "Boolean(p.node)" in page
    assert "appendPrevious" in page


def test_memory_page_does_not_use_sse_event_names_as_display_titles():
    page = (Path(__file__).parents[1] / "frontend" / "index.html").read_text(encoding="utf-8")
    # Event names remain in dispatch logic, but no fallback may display the raw
    # type/stage (for example, `event.type`) to the user.
    assert "p.title || p.stage || event.type" not in page
    assert "event.type;" not in page
    assert "user_message" in page


def test_memory_page_renders_final_order_summary_in_main_conversation():
    page = (Path(__file__).parents[1] / "frontend" / "index.html").read_text(encoding="utf-8")
    # The final business reply must be a normal assistant bubble in the main
    # conversation, rather than only a value in the right-side summary panel.
    assert "const getOrderSummary = result" in page
    assert "const getOrderUserMessage = result" in page
    assert "addBubble('assistant','InOrder',userMessage)" in page
    assert "state.messages.push({role:'assistant',content:userMessage})" in page
    assert "result?.order_summary" in page
    assert "liveBox.dataset.summaryAdded !== 'true'" in page


def test_memory_page_keeps_summary_compatibility_and_does_not_add_empty_reply():
    page = (Path(__file__).parents[1] / "frontend" / "index.html").read_text(encoding="utf-8")
    # Missing/empty summaries (for QA or old servers) must not create a fake
    # order reply, while the existing ordinary completion fallback remains.
    assert "typeof summary?.user_message === 'string'" in page
    assert "if (userMessage &&" in page
    assert "(state.last_result?.order_result?'订单信息已更新。':'已完成意图识别。')" in page


class CapturingGraph(FakeGraph):
    def __init__(self):
        super().__init__()
        self.states = []

    def invoke(self, state):
        self.states.append(state)
        return super().invoke(state)


def test_api_reference_time_is_valid_or_caller_supplied():
    graph = CapturingGraph()
    client = TestClient(create_app(main_graph=graph))
    client.post("/api/v2/chat", json={"session_id": "s", "message": "你好"})
    assert graph.states[0]["reference_time"]
    assert len(graph.states[0]["reference_time"]) == 16
    client.post("/api/v2/chat", json={"session_id": "s", "message": "你好", "reference_time": "2020-01-02 03:04"})
    assert graph.states[1]["reference_time"] == "2020-01-02 03:04"


def test_api_reuses_context_reference_time_over_request_value():
    graph = CapturingGraph()
    client = TestClient(create_app(main_graph=graph))
    client.post("/api/v2/chat", json={
        "session_id": "s", "message": "你好",
        "order_context": {"reference_time": "2020-01-02 03:04"},
        "reference_time": "2026-08-26 15:00",
    })
    state = graph.states[0]
    assert state["reference_time"] == "2020-01-02 03:04"
    assert state["order_context"].reference_time == "2020-01-02 03:04"


def test_api_rejects_invalid_reference_time_before_graph():
    graph = CapturingGraph()
    client = TestClient(create_app(main_graph=graph))
    response = client.post("/api/v2/chat", json={"session_id": "s", "message": "你好", "reference_time": "tomorrow"})
    assert response.status_code == 422
    assert graph.states == []


def test_api_error_is_terminal_without_done():
    client = TestClient(create_app(main_graph=FakeGraph(error=RuntimeError("secret"))))
    items = frames(client.post("/api/v2/chat", json={"session_id": "s", "message": "你好"}).text)
    assert items[-1]["type"] == "ERROR"
    assert all(item["type"] != "DONE" for item in items)


def test_timeout_error_is_non_retryable_and_terminal():
    client = TestClient(create_app(main_graph=FakeGraph(error=WorkflowTimeoutError())))
    items = frames(client.post("/api/v2/chat", json={"session_id": "s", "message": "你好"}).text)
    assert items[-1]["type"] == "ERROR"
    assert items[-1]["payload"] == {
        "code": "WORKFLOW_TIMEOUT", "message": "工作流处理超时", "stage": "intent", "retryable": False
    }
