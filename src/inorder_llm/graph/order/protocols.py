"""Minimal injectable protocols used by the order-processing graph."""

from typing import List, Protocol, Sequence, Mapping, Any

from ...context.models import HistoryConversation, OrderContext
from ...extract.models import Entity
from ...rewrite.models import RewriteResult
from ...cargo_profile.models import CargoProfileResult


class RewriteModel(Protocol):
    def rewrite(
        self,
        message: str,
        history: HistoryConversation,
        order_context: OrderContext,
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


__all__ = ["RewriteModel", "EntityExtractorModel", "CargoProfileModel"]
