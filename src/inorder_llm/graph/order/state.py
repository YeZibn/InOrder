"""State carried by the standalone order-processing subgraph."""

from typing import List, Optional, TypedDict

from ...context.models import HistoryConversation, OrderContext
from ...extract.models import Entity
from ...rewrite.models import RewriteResult


class OrderGraphState(TypedDict, total=False):
    message: str
    reference_time: str
    history: HistoryConversation
    order_context: OrderContext
    order_context_updated: bool
    cargo_updated: bool
    cargo_profile_updated: bool
    rewrite_result: RewriteResult
    entities: List[Entity]
    needs_clarification: bool
    clarification_reason: Optional[str]


__all__ = ["OrderGraphState"]
