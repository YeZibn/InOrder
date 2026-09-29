"""State carried by the standalone order-processing subgraph."""

from typing import List, Optional, TypedDict

from ...context.models import HistoryConversation, OrderContext
from ...extract.models import Entity
from ...rewrite.models import RewriteResult
from ...vehicle_resolution.models import VehicleResolutionResult
from ...order_summary.models import OrderSummary


class OrderGraphState(TypedDict, total=False):
    """Per-run order workspace with explicit field ownership.

    Request inputs (message, reference time, history, and user location) are
    read-only inputs. ``order_context`` is the sole cumulative order snapshot
    and is replaced with a copied working snapshot as nodes progress.
    ``entities`` is the current turn's instruction list: Extract writes raw
    entities and NormalizeEntities replaces that same field with normalized
    copies while retaining source text, action, and match metadata. Rewrite,
    vehicle resolution, and order summary are per-run results; the remaining
    booleans are execution/control metadata rather than order facts.
    """

    # Request inputs; nodes do not mutate these values.
    message: str
    reference_time: str
    deadline_at: float
    user_location: dict
    history: HistoryConversation
    # The only accumulated order snapshot inside the graph.
    order_context: OrderContext
    # Current-turn entities: raw after Extract, normalized after its boundary.
    entities: List[Entity]
    # Execution metadata and per-run derived results.
    order_context_updated: bool
    cargo_updated: bool
    vehicle_estimate_inputs_changed: bool
    cargo_profile_updated: bool
    rewrite_result: RewriteResult
    vehicle_resolution: VehicleResolutionResult
    order_summary: OrderSummary


__all__ = ["OrderGraphState"]
