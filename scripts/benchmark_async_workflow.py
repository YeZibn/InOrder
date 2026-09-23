"""Repeatable synthetic ASGI load probe (no external LLM calls).

Run: python scripts/benchmark_async_workflow.py --requests 64 --concurrency 8 32
"""

import argparse
import asyncio
import json
from pathlib import Path
import statistics
import sys
import threading
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import httpx
from langgraph.graph import END, START, StateGraph

from inorder_llm.graph.runnable import dual_node
from inorder_llm.infrastructure.llm.client import LLMClient
from inorder_llm.infrastructure.llm.config import LLMConfig
from inorder_llm.infrastructure.llm.models import ChatMessage
from inorder_llm.workflow.api import create_app
from inorder_llm.workflow.capacity import WorkerCapacity
from inorder_llm.workflow.runtime import WorkflowRuntimeConfig


class SyntheticTransport:
    def __init__(self, latency):
        self.latency = latency
        self.requests = 0
        self.active = 0
        self.peak = 0

    async def acomplete(self, messages, config, timeout=None):
        self.requests += 1
        self.active += 1
        self.peak = max(self.peak, self.active)
        try:
            await asyncio.sleep(self.latency)
            return type("Response", (), {"choices": [type("Choice", (), {"message": type("Message", (), {"content": "ok"})(), "finish_reason": "stop"})()], "model": "synthetic", "usage": None})()
        finally:
            self.active -= 1


class SyntheticNode:
    def __init__(self, client):
        self.client = client

    def __call__(self, state):
        raise AssertionError("API used the sync node entry")

    async def arun(self, state):
        await self.client.achat([ChatMessage("user", state["message"])], deadline_at=state["deadline_at"])
        return {"intent_result": {"main_intent": "qa"}}


async def probe(total, concurrency, latency):
    config = WorkflowRuntimeConfig()
    capacity = WorkerCapacity(config)
    transport = SyntheticTransport(latency)
    client = LLMClient(LLMConfig("synthetic", "https://example.test/v1", "synthetic", max_retries=0), transport=object(), async_transport=transport, llm_gate=capacity.llm)
    builder = StateGraph(dict)
    builder.add_node("synthetic_llm", dual_node(SyntheticNode(client)))
    builder.add_edge(START, "synthetic_llm")
    builder.add_edge("synthetic_llm", END)
    app = create_app(builder.compile(), runtime_config=config, capacity=capacity)
    semaphore = asyncio.Semaphore(concurrency)
    durations = []
    statuses = []
    lag_samples = []
    thread_peak = threading.active_count()
    stop = False

    async def heartbeat():
        nonlocal thread_peak
        while not stop:
            start = time.monotonic()
            await asyncio.sleep(0.005)
            lag_samples.append(max(0.0, time.monotonic() - start - 0.005))
            thread_peak = max(thread_peak, threading.active_count())

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as http:
        async def send(index):
            async with semaphore:
                start = time.monotonic()
                response = await http.post("/api/v2/chat", json={"session_id": str(index), "message": "hi"})
                durations.append(time.monotonic() - start)
                statuses.append(response.status_code)
                if response.status_code == 200:
                    assert '"type":"DONE"' in response.text

        monitor = asyncio.create_task(heartbeat())
        try:
            await asyncio.gather(*(send(i) for i in range(total)))
        finally:
            stop = True
            await monitor
            capacity.close()

    ordered = sorted(durations)
    return {
        "requests": total,
        "concurrency": concurrency,
        "synthetic_upstream_latency_ms": round(latency * 1000, 2),
        "p95_ms": round(ordered[max(0, int(0.95 * len(ordered)) - 1)] * 1000, 2),
        "mean_ms": round(statistics.mean(durations) * 1000, 2),
        "http_503_ratio": round(statuses.count(503) / total, 4),
        "event_loop_max_lag_ms": round(max(lag_samples, default=0) * 1000, 2),
        "thread_peak": thread_peak,
        "upstream_requests": transport.requests,
        "upstream_peak": transport.peak,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--requests", type=int, default=64)
    parser.add_argument("--concurrency", type=int, nargs="+", default=[8, 32])
    parser.add_argument("--latency-ms", type=float, default=50)
    args = parser.parse_args()
    for concurrency in args.concurrency:
        print(json.dumps(asyncio.run(probe(args.requests, concurrency, args.latency_ms / 1000)), ensure_ascii=False))


if __name__ == "__main__":
    main()
