import asyncio
import json
import threading
import time

import httpx
import pytest
from langgraph.graph import END, START, StateGraph

from inorder_llm.infrastructure.llm.errors import ConfigurationError
from inorder_llm.workflow.runtime import WorkflowRuntimeConfig
from inorder_llm.workflow.capacity import BoundedExecutor, CapacityGate, WorkflowOverloadedError
from inorder_llm.workflow.capacity import WorkerCapacity
from inorder_llm.workflow.api import create_app
from inorder_llm.graph.runnable import dual_node


def test_workflow_runtime_config_loads_finite_defaults_and_overrides():
    defaults = WorkflowRuntimeConfig.from_environ({})
    assert defaults.max_concurrency == 8
    assert defaults.max_waiting == 8
    assert defaults.queue_timeout_seconds == 5
    assert defaults.llm_max_concurrency == 8
    assert defaults.langextract_max_threads == 4
    assert defaults.workflow_timeout_seconds == 90

    configured = WorkflowRuntimeConfig.from_environ({
        "WORKFLOW_MAX_CONCURRENCY": "3",
        "WORKFLOW_MAX_WAITING": "0",
        "WORKFLOW_QUEUE_TIMEOUT_SECONDS": "0.25",
        "LLM_MAX_CONCURRENCY": "2",
        "LANGEXTRACT_MAX_THREADS": "1",
        "WORKFLOW_TIMEOUT_SECONDS": "12",
    })
    assert configured == WorkflowRuntimeConfig(3, 0, 0.25, 2, 1, 12)


@pytest.mark.parametrize("key,value", [
    ("WORKFLOW_MAX_CONCURRENCY", "0"),
    ("WORKFLOW_MAX_WAITING", "-1"),
    ("WORKFLOW_QUEUE_TIMEOUT_SECONDS", "nan"),
    ("LLM_MAX_CONCURRENCY", "x"),
    ("LANGEXTRACT_MAX_THREADS", "0"),
    ("WORKFLOW_TIMEOUT_SECONDS", "inf"),
])
def test_workflow_runtime_config_rejects_invalid_limits(key, value):
    with pytest.raises(ConfigurationError):
        WorkflowRuntimeConfig.from_environ({key: value})


def test_capacity_gate_bounds_waiters_and_releases_after_timeout():
    async def run():
        gate = CapacityGate(1, 1, 0.05)
        lease = await gate.acquire()
        queued = asyncio.create_task(gate.acquire())
        await asyncio.sleep(0.01)
        assert gate.waiting == 1
        with pytest.raises(WorkflowOverloadedError):
            await gate.acquire()
        with pytest.raises(WorkflowOverloadedError):
            await queued
        assert gate.active == 1 and gate.waiting == 0
        await lease.release()
        assert gate.active == 0

    asyncio.run(run())


def test_full_workflow_capacity_returns_json_before_sse():
    async def run():
        config = WorkflowRuntimeConfig(max_concurrency=1, max_waiting=0)
        app = create_app(runtime_config=config)
        lease = await app.state.workflow_gate.acquire()
        try:
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
                response = await client.post("/api/v2/chat", json={"session_id": "s", "message": "测试"})
            assert response.status_code == 503
            assert response.json()["error"]["code"] == "WORKFLOW_OVERLOADED"
            assert response.headers["content-type"].startswith("application/json")
        finally:
            await lease.release()

    asyncio.run(run())


def test_waiting_admission_stops_on_disconnect_or_deadline():
    async def run():
        gate = CapacityGate(1, 2, 0.5)
        lease = await gate.acquire()
        disconnected = False

        async def is_disconnected():
            return disconnected

        waiting = asyncio.create_task(gate.acquire(disconnected=is_disconnected))
        await asyncio.sleep(0.01)
        disconnected = True
        with pytest.raises(asyncio.CancelledError):
            await waiting
        with pytest.raises(WorkflowOverloadedError):
            await gate.acquire(deadline_at=time.monotonic() + 0.01, deadline_is_overload=True)
        assert gate.waiting == 0
        await lease.release()

    asyncio.run(run())


def test_cancelled_waiter_does_not_release_running_thread_slot():
    async def run():
        executor = BoundedExecutor(1, 0, 0.05, "test-bounded")
        started, finish = threading.Event(), threading.Event()

        def slow():
            started.set()
            finish.wait(1)

        try:
            task = asyncio.create_task(executor.run(slow))
            assert await asyncio.to_thread(started.wait, 0.5)
            task.cancel()
            with pytest.raises(asyncio.CancelledError):
                await task
            assert executor.gate.active == 1
            with pytest.raises(WorkflowOverloadedError):
                await executor.run(lambda: None)
            finish.set()
            for _ in range(20):
                if executor.gate.active == 0:
                    break
                await asyncio.sleep(0.01)
            assert executor.gate.active == 0
        finally:
            finish.set()
            executor.close()

    asyncio.run(run())


def test_cancelled_langextract_keeps_shared_llm_and_thread_slots_until_worker_finishes():
    async def run():
        executor = BoundedExecutor(1, 0, 0.05, "test-langextract")
        llm = CapacityGate(1, 0, 0.05)
        started, finish = threading.Event(), threading.Event()
        def slow():
            started.set()
            finish.wait(1)
        try:
            task = asyncio.create_task(executor.run(slow, additional_gate=llm))
            assert await asyncio.to_thread(started.wait, 0.5)
            task.cancel()
            with pytest.raises(asyncio.CancelledError):
                await task
            assert executor.gate.active == 1 and llm.active == 1
            with pytest.raises(WorkflowOverloadedError):
                await llm.acquire()
            finish.set()
            for _ in range(20):
                if executor.gate.active == 0 and llm.active == 0:
                    break
                await asyncio.sleep(0.01)
            assert executor.gate.active == 0 and llm.active == 0
        finally:
            finish.set()
            executor.close()
    asyncio.run(run())


def test_dual_node_uses_bounded_thread_for_async_graph_and_keeps_sync_entry():
    capacity = WorkerCapacity(WorkflowRuntimeConfig())

    def record_thread(state):
        return {"thread_name": threading.current_thread().name}

    builder = StateGraph(dict)
    builder.add_node("record", dual_node(record_thread, capacity.sync_nodes))
    builder.add_edge(START, "record")
    builder.add_edge("record", END)
    graph = builder.compile()
    try:
        assert graph.invoke({})["thread_name"] == threading.current_thread().name

        async def run():
            return [update async for update in graph.astream({}, stream_mode="updates")]

        updates = asyncio.run(run())
        assert updates[0]["record"]["thread_name"].startswith("inorder-node")
    finally:
        capacity.close()


def test_slow_sync_workflow_does_not_block_another_request():
    async def run():
        config = WorkflowRuntimeConfig(max_concurrency=2, max_waiting=0, queue_timeout_seconds=0.5)
        capacity = WorkerCapacity(config)
        started, finish = threading.Event(), threading.Event()

        def operation(state):
            if state["message"] == "slow":
                started.set()
                finish.wait(1)
            return {"intent_result": {"main_intent": "qa"}, "order_graph_entered": False}

        builder = StateGraph(dict)
        builder.add_node("respond", dual_node(operation, capacity.sync_nodes))
        builder.add_edge(START, "respond")
        builder.add_edge("respond", END)
        app = create_app(builder.compile(), runtime_config=config, capacity=capacity)
        try:
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
                slow = asyncio.create_task(client.post("/api/v2/chat", json={"session_id": "s", "message": "slow"}))
                assert await asyncio.to_thread(started.wait, 0.5)
                fast = await asyncio.wait_for(client.post("/api/v2/chat", json={"session_id": "f", "message": "fast"}), 0.5)
                assert fast.status_code == 200
                assert any(json.loads(line[6:])["type"] == "DONE" for line in fast.text.splitlines() if line.startswith("data: "))
                finish.set()
                assert (await asyncio.wait_for(slow, 1)).status_code == 200
            assert capacity.workflow.active == 0
            assert capacity.sync_nodes.gate.active == 0
        finally:
            finish.set()
            capacity.close()

    asyncio.run(run())


def test_async_graph_deadline_ends_sse_once_while_sync_worker_finishes_later():
    async def run():
        config = WorkflowRuntimeConfig(workflow_timeout_seconds=0.05)
        capacity = WorkerCapacity(config)
        started, finish = threading.Event(), threading.Event()

        def slow(_state):
            started.set()
            finish.wait(1)
            return {"intent_result": {"main_intent": "qa"}}

        builder = StateGraph(dict)
        builder.add_node("slow", dual_node(slow, capacity.sync_nodes))
        builder.add_edge(START, "slow")
        builder.add_edge("slow", END)
        app = create_app(builder.compile(), runtime_config=config, capacity=capacity)
        try:
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
                request = asyncio.create_task(client.post("/api/v2/chat", json={"session_id": "s", "message": "slow"}))
                assert await asyncio.to_thread(started.wait, 0.5)
                response = await asyncio.wait_for(request, 0.5)
            payloads = [json.loads(line[6:]) for line in response.text.splitlines() if line.startswith("data: ")]
            assert [item["type"] for item in payloads] == ["THINKING_START", "ERROR"]
            assert payloads[-1]["payload"]["code"] == "WORKFLOW_TIMEOUT"
            assert capacity.sync_nodes.gate.active == 1
            finish.set()
            for _ in range(20):
                if capacity.sync_nodes.gate.active == 0:
                    break
                await asyncio.sleep(0.01)
            assert capacity.sync_nodes.gate.active == 0
        finally:
            finish.set()
            capacity.close()

    asyncio.run(run())


def test_cancelled_sse_releases_workflow_but_keeps_running_thread_counted():
    async def run():
        config = WorkflowRuntimeConfig(max_concurrency=1, max_waiting=0)
        capacity = WorkerCapacity(config)
        started, finish = threading.Event(), threading.Event()

        def slow(_state):
            started.set()
            finish.wait(1)
            return {"intent_result": {"main_intent": "qa"}}

        builder = StateGraph(dict)
        builder.add_node("slow", dual_node(slow, capacity.sync_nodes))
        builder.add_edge(START, "slow")
        builder.add_edge("slow", END)
        app = create_app(builder.compile(), runtime_config=config, capacity=capacity)
        try:
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
                request = asyncio.create_task(client.post("/api/v2/chat", json={"session_id": "s", "message": "slow"}))
                assert await asyncio.to_thread(started.wait, 0.5)
                request.cancel()
                with pytest.raises(asyncio.CancelledError):
                    await request
            for _ in range(20):
                if capacity.workflow.active == 0:
                    break
                await asyncio.sleep(0.01)
            assert capacity.workflow.active == 0
            assert capacity.sync_nodes.gate.active == 1
            finish.set()
            for _ in range(20):
                if capacity.sync_nodes.gate.active == 0:
                    break
                await asyncio.sleep(0.01)
            assert capacity.sync_nodes.gate.active == 0
        finally:
            finish.set()
            capacity.close()

    asyncio.run(run())
