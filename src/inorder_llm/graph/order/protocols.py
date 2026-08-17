"""Minimal injectable protocols used by the order-processing graph."""

from typing import List, Protocol

from ...context.models import HistoryConversation, OrderContext
from ...extract.models import Entity
from ...rewrite.models import RewriteResult


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


__all__ = ["RewriteModel", "EntityExtractorModel"]
