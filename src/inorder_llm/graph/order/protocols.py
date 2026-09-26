"""Minimal injectable protocols used by the order-processing graph."""

from typing import List, Optional, Protocol, Sequence, Mapping, Any

from ...context.models import HistoryConversation, OrderContext
from ...extract.models import Entity
from ...rewrite.models import RewriteResult
from ...cargo_profile.models import CargoProfileResult
from ...vehicle_resolution.models import VehicleResolutionResult


class RewriteModel(Protocol):
    def rewrite(
        self,
        message: str,
        history: HistoryConversation,
        order_context: OrderContext,
        reference_time: Optional[str] = None,
    ) -> RewriteResult:
        ...


class EntityExtractorModel(Protocol):
    def extract(
        self,
        message: str,
        reference_time: str,
    ) -> List[Entity]:
        ...


class CargoProfileModel(Protocol):
    def profile(self, cargo: Sequence[Mapping[str, Any]]) -> CargoProfileResult:
        ...


class VehicleResolutionModel(Protocol):
    def resolve(
        self,
        cargo_profiles: Sequence[Mapping[str, Any]],
        cargo_profile_summary: Mapping[str, Any] | None,
        raw_vehicle_text: str | None = None,
        effective_city: str | None = None,
        vehicle_specs: Sequence[str] = (),
    ) -> VehicleResolutionResult:
        ...


__all__ = ["RewriteModel", "EntityExtractorModel", "CargoProfileModel", "VehicleResolutionModel"]
