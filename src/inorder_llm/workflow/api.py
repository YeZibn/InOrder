"""HTTP/SSE boundary for the full LangGraph workflow."""

import asyncio
import time
from contextlib import asynccontextmanager
from copy import deepcopy
from pathlib import Path
from typing import Any, Callable, Iterator, Optional

from ..context import HistoryConversation, OrderContext
from ..context.recovery import ConversationRecovery, prepare_conversation_recovery
from ..context.summary import summarize_assistant
from ..reference_time import ReferenceTimeError, resolve_context_reference_time
from .adapter import WorkflowEventAdapter
from .capacity import CapacityLease, WorkerCapacity, WorkflowOverloadedError
from .events import error_event
from .runtime import WorkflowRuntimeConfig

try:
    from fastapi import FastAPI, Request
    from fastapi.responses import JSONResponse, StreamingResponse
    from pydantic import BaseModel, Field, ValidationError
except ImportError:  # pragma: no cover
    FastAPI = None


def _context(value: Any) -> OrderContext:
    if value is None:
        return OrderContext()
    if isinstance(value, OrderContext):
        return value
    if not isinstance(value, dict):
        raise ValueError("order_context must be an object")
    fields = set(OrderContext.__dataclass_fields__)
    return OrderContext(**{key: value[key] for key in fields if key in value})


def _history(value: Any) -> HistoryConversation:
    if value is None:
        return HistoryConversation()
    if isinstance(value, HistoryConversation):
        return value
    if not isinstance(value, dict) or not isinstance(value.get("turns", []), list):
        raise ValueError("history must contain a turns array")
    history = HistoryConversation()
    for turn in value["turns"]:
        if not isinstance(turn, dict) or turn.get("role") not in ("user", "assistant", "system") or not turn.get("content"):
            raise ValueError("history turns must contain role and non-empty content")
        history.append(turn["role"], turn["content"], turn.get("metadata"))
    return history


def create_app(main_graph=None, graph_factory: Optional[Callable[[], Any]] = None, runtime_config: WorkflowRuntimeConfig | None = None, capacity: WorkerCapacity | None = None, shutdown_callback=None):
    if FastAPI is None:
        raise RuntimeError("SSE API requires fastapi and uvicorn")
    runtime_config = runtime_config or WorkflowRuntimeConfig.from_environ()
    capacity = capacity or WorkerCapacity(runtime_config)

    @asynccontextmanager
    async def lifespan(_app):
        try:
            yield
        finally:
            try:
                if shutdown_callback is not None:
                    await shutdown_callback()
            finally:
                capacity.close()

    app = FastAPI(title="InOrder API", version="2", lifespan=lifespan)
    app.state.workflow_config = runtime_config
    app.state.capacity = capacity
    app.state.workflow_gate = capacity.workflow

    class AdmittedStreamingResponse(StreamingResponse):
        def __init__(self, *args, lease: CapacityLease, **kwargs):
            super().__init__(*args, **kwargs)
            self._lease = lease

        async def __call__(self, scope, receive, send):
            try:
                await super().__call__(scope, receive, send)
            finally:
                await asyncio.shield(self._lease.release())

    frontend_path = Path(__file__).resolve().parents[3] / "frontend" / "index.html"

    @app.get("/", include_in_schema=False)
    async def index():
        if not frontend_path.is_file():
            return JSONResponse({"error": {"code": "UI_NOT_FOUND", "message": "frontend/index.html not found"}}, status_code=404)
        from fastapi.responses import HTMLResponse
        return HTMLResponse(frontend_path.read_text(encoding="utf-8"))

    class ChatRequest(BaseModel):
        session_id: str = Field(min_length=1)
        message: str = Field(min_length=1)
        history: Optional[dict] = None
        order_context: Optional[dict] = None
        reference_time: Optional[str] = None
        user_location: Optional[dict] = None

    def resolve_graph():
        graph = main_graph or (graph_factory() if graph_factory else None)
        if graph is None:
            raise RuntimeError("main graph is not configured")
        return graph

    @app.post("/api/v2/chat")
    async def chat(request: Request):
        try:
            body = await request.json()
            payload = ChatRequest.model_validate(body)
            if not payload.message.strip():
                raise ValueError("message must not be empty")
            order_context = _context(payload.order_context)
            resolved_reference_time = resolve_context_reference_time(
                order_context.reference_time, payload.reference_time
            )
            order_context = deepcopy(order_context)
            order_context.reference_time = resolved_reference_time
            history = _history(payload.history)
            recovery = prepare_conversation_recovery(history, payload.message)
            state_history = recovery.history
            state = {
                "session_id": payload.session_id,
                "message": recovery.message,
                "history": state_history,
                "order_context": order_context,
                "reference_time": resolved_reference_time,
                "user_location": payload.user_location or {},
                "deadline_at": time.monotonic() + runtime_config.workflow_timeout_seconds,
            }
        except (ValidationError, ReferenceTimeError, ValueError, TypeError) as exc:
            return JSONResponse({"error": {"code": "INVALID_REQUEST", "message": str(exc)}}, status_code=422)

        try:
            lease = await capacity.workflow.acquire(
                deadline_at=state["deadline_at"],
                disconnected=request.is_disconnected,
                deadline_is_overload=True,
            )
        except WorkflowOverloadedError:
            return JSONResponse(
                {"error": {"code": "WORKFLOW_OVERLOADED", "message": "服务繁忙，请稍后重试"}},
                status_code=503,
            )

        async def stream():
            try:
                async for event in WorkflowEventAdapter(resolve_graph()).aevents(state):
                    if await request.is_disconnected():
                        return
                    if event.type.value == "DONE":
                        event = _with_recovery_history(event, recovery, state_history)
                    yield event.frame()
            except Exception as exc:
                yield error_event(exc).frame()

        return AdmittedStreamingResponse(stream(), lease=lease, media_type="text/event-stream", headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})

    return app


def _with_recovery_history(event, recovery: ConversationRecovery, history: HistoryConversation):
    """Attach a replaceable history snapshot to a successful DONE event."""
    from .events import EventType, WorkflowEvent
    if event.type is not EventType.DONE:
        return event
    result = event.payload.get("result", {})
    assistant, base_metadata = summarize_assistant(result) if isinstance(result, dict) else ("", {})
    completed = HistoryConversation()
    completed.turns = list(history.turns)
    if not completed.turns or completed.turns[-1].role != "user" or completed.turns[-1].content != recovery.message:
        completed.append_user(recovery.message)
    if assistant:
        completed.append_assistant(assistant, {"recovered": recovery.recovered, **base_metadata})
    payload = dict(event.payload)
    payload["history"] = completed.to_dict()
    payload["history_recovered"] = recovery.recovered
    return WorkflowEvent(EventType.DONE, payload)


__all__ = ["create_app"]
