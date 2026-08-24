"""State shared by the main parent graph and its child graphs."""

from typing import Any, Dict, Optional, TypedDict

from ...context.models import HistoryConversation, OrderContext
from ...intent.models import IntentPlan


class MainGraphState(TypedDict, total=False):
    message: str
    history: HistoryConversation
    order_context: OrderContext
    reference_time: str
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
    order_graph_entered: bool
    rewrite_completed: bool
    extract_executed: bool
    entity_count: int
    extract_skipped_reason: Optional[str]
    qa_placeholder: Optional[str]


__all__ = ["MainGraphState"]
