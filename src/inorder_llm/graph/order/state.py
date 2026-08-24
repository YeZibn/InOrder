"""State carried by the standalone order-processing subgraph."""

from typing import List, Optional, TypedDict

from ...context.models import HistoryConversation, OrderContext
from ...extract.models import Entity
from ...rewrite.models import RewriteResult
from ...vehicle_resolution.models import VehicleResolutionResult


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
    vehicle_resolution: VehicleResolutionResult


__all__ = ["OrderGraphState"]
