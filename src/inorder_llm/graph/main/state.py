"""State shared by the main parent graph and its child graphs."""

from typing import Any, Dict, Optional, TypedDict

from ...context.models import HistoryConversation, OrderContext
from ...intent.models import IntentPlan


class MainGraphState(TypedDict, total=False):
    """Internal parent-graph workspace.

    ``order_context`` is the one working snapshot passed into the order child;
    the finalized public result projects it only through ``order_result``.
    Intent, order-child outputs, and routing flags are per-run results or
    control metadata, not additional persisted order state.
    """

    message: str
    history: HistoryConversation
    order_context: OrderContext
    reference_time: str
    deadline_at: float
    user_location: Dict[str, Any]
    main_intent: str
    main_confidence: Optional[float]
    intent_plan: IntentPlan
    intent_result: Dict[str, Any]
    order_result: Dict[str, Any]
    rewrite_result: Any
    entities: list
    order_context_updated: bool
    cargo_profile_updated: bool
    vehicle_resolution: Any
    order_summary: Any
    order_graph_entered: bool
    rewrite_completed: bool
    extract_executed: bool
    entity_count: int
    extract_skipped_reason: Optional[str]
    qa_placeholder: Optional[str]


class MainGraphOutput(TypedDict, total=False):
    """Caller-facing projection; internal working context is intentionally absent."""

    intent_result: Dict[str, Any]
    order_result: Dict[str, Any]
    order_graph_entered: bool
    qa_placeholder: Optional[str]


__all__ = ["MainGraphState", "MainGraphOutput"]
