"""Async transport, retry, deadline, and native-node contract tests."""

import asyncio
import json
import time
from types import SimpleNamespace

import pytest

from inorder_llm.infrastructure.llm.client import LLMClient
from inorder_llm.infrastructure.llm.config import LLMConfig
from inorder_llm.infrastructure.llm.errors import AuthenticationError, WorkflowTimeoutError
from inorder_llm.infrastructure.llm.models import ChatMessage
from inorder_llm.infrastructure.llm.structured import acall_with_format_repair
from inorder_llm.infrastructure.llm.transport import AsyncOpenAITransport
from inorder_llm.graph.intent.nodes.intent_nodes import MainIntentNode
from inorder_llm.graph.runnable import dual_node
from inorder_llm.workflow.capacity import CapacityGate
from inorder_llm.workflow.capacity import WorkerCapacity
from inorder_llm.workflow.runtime import WorkflowRuntimeConfig
from inorder_llm.workflow.api import create_app
from langgraph.graph import StateGraph, START, END
import httpx


def _config(**overrides):
    values = dict(api_key="test", base_url="https://example.test/v1", model="demo", max_retries=2, backoff_seconds=0, timeout=0.2)
    values.update(overrides)
    return LLMConfig(**values)


def _response(text="ok"):
    return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=text), finish_reason="stop")], model="demo", usage=None)


class FakeAsyncTransport:
    def __init__(self, replies):
        self.replies = list(replies)
        self.calls = 0

    async def acomplete(self, messages, config, timeout=None):
        self.calls += 1
        answer = self.replies.pop(0)
        if isinstance(answer, Exception):
            raise answer
        if callable(answer):
            return await answer()
        return answer

    async def astream(self, messages, config, timeout=None):
        self.calls += 1
        answer = self.replies.pop(0)
        if isinstance(answer, Exception):
            raise answer
        async def events():
            for item in answer:
                if isinstance(item, Exception):
                    raise item
                yield item
        return events()


def test_async_retries_only_transport_attempts_and_releases_llm_slots():
    async def run():
        transport = FakeAsyncTransport([ConnectionError("upstream"), ConnectionError("upstream"), _response()])
        gate = CapacityGate(1, 1, 0.1)
        client = LLMClient(_config(), transport=object(), async_transport=transport, llm_gate=gate)
        result = await client.achat([ChatMessage("user", "hi")])
        assert result.text == "ok" and transport.calls == 3
        assert gate.active == 0
    asyncio.run(run())


def test_async_fatal_error_does_not_retry():
    async def run():
        rejected = Exception("forbidden")
        rejected.status_code = 403
        transport = FakeAsyncTransport([rejected, _response()])
        client = LLMClient(_config(), transport=object(), async_transport=transport)
        with pytest.raises(AuthenticationError):
            await client.achat([ChatMessage("user", "hi")])
        assert transport.calls == 1
    asyncio.run(run())


def test_async_unknown_upstream_error_does_not_retry_without_transient_evidence():
    async def run():
        transport = FakeAsyncTransport([RuntimeError("unexpected"), _response()])
        client = LLMClient(_config(), transport=object(), async_transport=transport)
        with pytest.raises(Exception):
            await client.achat([ChatMessage("user", "hi")])
        assert transport.calls == 1
    asyncio.run(run())


def test_async_retry_after_cannot_cross_deadline():
    async def run():
        limited = Exception("rate limit")
        limited.status_code = 429
        limited.response = SimpleNamespace(headers={"retry-after": "10"})
        transport = FakeAsyncTransport([limited, _response()])
        client = LLMClient(_config(), transport=object(), async_transport=transport)
        with pytest.raises(WorkflowTimeoutError):
            await client.achat([ChatMessage("user", "hi")], deadline_at=time.monotonic() + 0.1)
        assert transport.calls == 1
    asyncio.run(run())


def test_async_request_deadline_applies_during_upstream_wait():
    async def slow():
        await asyncio.sleep(1)
        return _response()
    async def run():
        transport = FakeAsyncTransport([slow])
        client = LLMClient(_config(max_retries=0), transport=object(), async_transport=transport)
        with pytest.raises(WorkflowTimeoutError):
            await client.achat([ChatMessage("user", "hi")], deadline_at=time.monotonic() + 0.02)
        assert transport.calls == 1
    asyncio.run(run())


def test_async_format_repair_is_one_separate_request():
    async def run():
        transport = FakeAsyncTransport([_response("bad"), _response("42")])
        client = LLMClient(_config(), transport=object(), async_transport=transport)
        result = await acall_with_format_repair(client, [ChatMessage("user", "number")], int, "try again")
        assert result == 42 and transport.calls == 2
    asyncio.run(run())


def test_async_stream_does_not_replay_after_content_delivery():
    async def run():
        event = SimpleNamespace(choices=[SimpleNamespace(delta=SimpleNamespace(content="part"), finish_reason=None)], model="demo", usage=None)
        transport = FakeAsyncTransport([[event, RuntimeError("failed")], [event]])
        received = []
        client = LLMClient(_config(streaming=True), transport=object(), async_transport=transport)
        with pytest.raises(Exception):
            await client.astream([ChatMessage("user", "hi")], on_delta=received.append)
        assert received == ["part"] and transport.calls == 1
    asyncio.run(run())


def test_async_transport_both_api_modes_and_sdk_retry_disabled(monkeypatch):
    import openai
    calls = []
    class Resource:
        async def create(self, **request):
            calls.append(request)
            return _response()
    class SDK:
        def __init__(self, **kwargs):
            calls.append(kwargs)
            self.chat = SimpleNamespace(completions=Resource())
            self.responses = Resource()
        async def close(self):
            calls.append("closed")
    monkeypatch.setattr(openai, "AsyncOpenAI", SDK)
    async def run():
        for mode in ("chat_completions", "responses"):
            cfg = _config(api_mode=mode)
            transport = AsyncOpenAITransport(cfg)
            await transport.acomplete([ChatMessage("user", "hi")], cfg)
            await transport.astream([ChatMessage("user", "hi")], cfg)
            await transport.aclose()
        assert calls[0]["max_retries"] == 0
        assert calls[1]["messages"][0]["content"] == "hi"
        assert calls[2]["stream"] is True
        assert calls[4]["max_retries"] == 0
        assert calls[5]["input"][0]["content"] == "hi"
        assert calls[6]["stream"] is True
    asyncio.run(run())


def test_intent_node_native_async_path_avoids_sync_model():
    class AsyncModel:
        def classify_main_intent(self, message):
            raise AssertionError("sync path called")
        async def aclassify_main_intent(self, message, deadline_at=None):
            return {"main_intent": "qa", "confidence": 0.9}
    async def run():
        result = await dual_node(MainIntentNode(AsyncModel())).ainvoke({"message": "hi"})
        assert result["main_intent"] == "qa"
    asyncio.run(run())


def test_async_parent_graph_uses_native_intent_rewrite_and_json_extraction():
    from inorder_llm.context import HistoryConversation, OrderContext
    from inorder_llm.graph.main import build_main_graph_from_models
    from inorder_llm.intent.resolver import LLMIntentModel
    from inorder_llm.rewrite.resolver import OrderRewriteModel
    from inorder_llm.extract.resolver import EntityExtractor
    async def run():
        replies = [
            _response('{"main_intent":"order","confidence":0.9}'),
            _response('{"rewritten_text":"发货","extraction_text":"发货"}'),
            _response('{"entities":[]}'),
        ]
        transport = FakeAsyncTransport(replies)
        client = LLMClient(_config(max_retries=0), transport=object(), async_transport=transport)
        graph = build_main_graph_from_models(LLMIntentModel(client), OrderRewriteModel(client), EntityExtractor(client))
        result = await graph.ainvoke({"message": "发货", "history": HistoryConversation(), "order_context": OrderContext(), "reference_time": "2026-08-24 10:00"})
        assert result["order_graph_entered"] is True
        assert result["entities"] == []
        assert transport.calls == 3
    asyncio.run(run())


def test_async_cargo_profile_preserves_copy_and_replaces_derived_fields():
    from inorder_llm.cargo_profile.resolver import CargoProfileResolver
    from inorder_llm.context import OrderContext
    from inorder_llm.graph.order.nodes import CargoProfileNode
    async def run():
        raw = {"name": "香蕉", "weight": ["1吨"], "quantity": [], "volume": [], "dimensions": []}
        profile = {"name": "香蕉", "weight_kg": 1000.0, "volume_m3": 1.8,
                   "dimensions_cm": {"length": 120.0, "width": 100.0, "height": 150.0},
                   "stackability": "partial", "fragility": "low", "temperature": "cool", "reason": "估算。"}
        payload = {"cargo_profiles": [profile], "cargo_profile_summary": {"total_weight_kg": 1000.0, "total_volume_m3": 1.8, "reason": "汇总。"}}
        transport = FakeAsyncTransport([_response(json.dumps(payload, ensure_ascii=False))])
        client = LLMClient(_config(max_retries=0), transport=object(), async_transport=transport)
        old = OrderContext(cargo=[raw], cargo_profiles=[{"name": "旧货物"}])
        result = await CargoProfileNode(CargoProfileResolver(client)).arun({"order_context": old})
        assert old.cargo_profiles == [{"name": "旧货物"}]
        assert result["order_context"].cargo_profiles[0]["name"] == "香蕉"
        assert result["cargo_profile_updated"] is True
    asyncio.run(run())


def test_dependency_queue_expiry_is_single_sse_overload_error():
    class LLMNode:
        def __init__(self, client):
            self.client = client
        def __call__(self, state):
            raise AssertionError("sync path called")
        async def arun(self, state):
            assert self.client._llm_gate.active == 1
            await self.client.achat([ChatMessage("user", "hello")], deadline_at=state["deadline_at"])
            return {"intent_result": {"main_intent": "qa"}}
    async def run():
        config = WorkflowRuntimeConfig(max_concurrency=1, llm_max_concurrency=1, queue_timeout_seconds=0.02)
        capacity = WorkerCapacity(config)
        transport = FakeAsyncTransport([_response()])
        client = LLMClient(_config(), transport=object(), async_transport=transport, llm_gate=capacity.llm)
        builder = StateGraph(dict)
        builder.add_node("llm", dual_node(LLMNode(client)))
        builder.add_edge(START, "llm")
        builder.add_edge("llm", END)
        app = create_app(builder.compile(), runtime_config=config, capacity=capacity)
        lease = await capacity.llm.acquire()
        try:
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as http:
                response = await http.post("/api/v2/chat", json={"session_id": "s", "message": "hi"})
            payloads = [json.loads(line[6:]) for line in response.text.splitlines() if line.startswith("data: ")]
            assert [item["type"] for item in payloads] == ["THINKING_START", "ERROR"], payloads
            assert payloads[-1]["payload"]["code"] == "WORKFLOW_OVERLOADED"
            assert payloads[-1]["payload"]["retryable"] is True
            assert transport.calls == 0
        finally:
            await lease.release()
            capacity.close()
    asyncio.run(run())
