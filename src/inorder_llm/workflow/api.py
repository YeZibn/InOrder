"""HTTP/SSE boundary for the full LangGraph workflow."""

import os
import time
from copy import deepcopy
from pathlib import Path
from typing import Any, Callable, Iterator, Optional

from ..context import HistoryConversation, OrderContext
from ..context.recovery import ConversationRecovery, prepare_conversation_recovery
from ..context.summary import summarize_assistant
from ..reference_time import ReferenceTimeError, resolve_context_reference_time
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
                "deadline_at": time.monotonic() + float(os.getenv("WORKFLOW_TIMEOUT_SECONDS", "90")),
            }
        except (ValidationError, ReferenceTimeError, ValueError, TypeError) as exc:
            return JSONResponse({"error": {"code": "INVALID_REQUEST", "message": str(exc)}}, status_code=422)

        async def stream():
            try:
                for event in WorkflowEventAdapter(resolve_graph()).events(state):
                    if await request.is_disconnected():
                        return
                    if event.type.value == "DONE":
                        event = _with_recovery_history(event, recovery, state_history)
                    yield event.frame()
            except BaseException as exc:
                yield error_event(exc).frame()

        return StreamingResponse(stream(), media_type="text/event-stream", headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})

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
