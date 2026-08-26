"""HTTP/SSE boundary for the full LangGraph workflow."""

import os
import time
from typing import Any, Callable, Iterator, Optional

from ..context import HistoryConversation, OrderContext
from ..reference_time import ReferenceTimeError, resolve_reference_time
from .adapter import WorkflowEventAdapter
from .events import error_event

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


def create_app(main_graph=None, graph_factory: Optional[Callable[[], Any]] = None):
    if FastAPI is None:
        raise RuntimeError("SSE API requires fastapi and uvicorn")
    app = FastAPI(title="InOrder API", version="2")

    class ChatRequest(BaseModel):
        session_id: str = Field(min_length=1)
        message: str = Field(min_length=1)
        history: Optional[dict] = None
        order_context: Optional[dict] = None
        reference_time: Optional[str] = None

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
            resolved_reference_time = resolve_reference_time(payload.reference_time)
            state = {
                "session_id": payload.session_id,
                "message": payload.message,
                "history": _history(payload.history),
                "order_context": _context(payload.order_context),
                "reference_time": resolved_reference_time,
                "deadline_at": time.monotonic() + float(os.getenv("WORKFLOW_TIMEOUT_SECONDS", "90")),
            }
        except (ValidationError, ReferenceTimeError, ValueError, TypeError) as exc:
            return JSONResponse({"error": {"code": "INVALID_REQUEST", "message": str(exc)}}, status_code=422)

        async def stream():
            try:
                for event in WorkflowEventAdapter(resolve_graph()).events(state):
                    if await request.is_disconnected():
                        return
                    yield event.frame()
            except BaseException as exc:
                yield error_event(exc).frame()

        return StreamingResponse(stream(), media_type="text/event-stream", headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})

    return app


__all__ = ["create_app"]
