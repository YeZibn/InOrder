"""State carried by the standalone order-processing subgraph."""

from typing import List, Optional, TypedDict

from ...context.models import HistoryConversation, OrderContext
from ...extract.models import Entity
from ...rewrite.models import RewriteResult
from ...vehicle_resolution.models import VehicleResolutionResult
from ...order_summary.models import OrderSummary


class OrderGraphState(TypedDict, total=False):
    message: str
    reference_time: str
    deadline_at: float
    user_location: dict
    history: HistoryConversation
    order_context: OrderContext
    order_context_updated: bool
    cargo_updated: bool
    vehicle_estimate_inputs_changed: bool
    cargo_profile_updated: bool
    rewrite_result: RewriteResult
    entities: List[Entity]
    vehicle_resolution: VehicleResolutionResult
    order_summary: OrderSummary


__all__ = ["OrderGraphState"]
