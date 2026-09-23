"""Sync/async LangGraph node entry points with bounded sync fallback."""

import asyncio
import time
from typing import Any

from langchain_core.runnables import RunnableLambda

from ..infrastructure.llm.errors import WorkflowTimeoutError


def dual_node(operation: Any, executor: Any = None, additional_gate: Any = None) -> RunnableLambda:
    async def async_call(state):
        deadline = state.get("deadline_at") if isinstance(state, dict) else None
        if deadline is not None and time.monotonic() >= deadline:
            raise WorkflowTimeoutError("workflow deadline exceeded before node")
        native = getattr(operation, "arun", None)
        supports_async = getattr(operation, "supports_async", None)
        if callable(native) and (not callable(supports_async) or supports_async()):
            return await native(state)
        if executor is not None:
            return await executor.run(operation, state, deadline_at=deadline, additional_gate=additional_gate)
        return await asyncio.to_thread(operation, state)

    return RunnableLambda(operation, afunc=async_call)
