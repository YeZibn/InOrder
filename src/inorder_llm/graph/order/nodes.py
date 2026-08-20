"""Nodes for the standalone order-processing subgraph."""

from typing import Any, Dict, Literal

from ...graph.base import BaseNode
from ...context import OrderContextReducer
from .protocols import CargoProfileModel, EntityExtractorModel, RewriteModel
from .state import OrderGraphState


class RewriteNode(BaseNode[OrderGraphState]):
    name = "rewrite"

    def __init__(self, model: RewriteModel):
        self.model = model

    def run(self, state: OrderGraphState) -> Dict[str, Any]:
        result = self.model.rewrite(
            state["message"], state["history"], state["order_context"]
        )
        return {
            "rewrite_result": result,
        }


class ExtractNode(BaseNode[OrderGraphState]):
    name = "extract"

    def __init__(self, extractor: EntityExtractorModel):
        self.extractor = extractor

    def run(self, state: OrderGraphState) -> Dict[str, Any]:
        rewrite_result = state["rewrite_result"]
        entities = self.extractor.extract(
            rewrite_result.extraction_text,
            state["reference_time"],
        )
        return {"entities": entities}


class ContextUpdateNode(BaseNode[OrderGraphState]):
    """Apply extracted actions to a copied order context."""

    name = "update_context"

    def __init__(self, reducer: OrderContextReducer | None = None):
        self.reducer = reducer or OrderContextReducer()

    def run(self, state: OrderGraphState) -> Dict[str, Any]:
        original = state["order_context"]
        updated = self.reducer.apply(original, state.get("entities", []))
        return {
            "order_context": updated,
            "order_context_updated": updated != original,
            "cargo_updated": updated.cargo != original.cargo,
        }


class CargoProfileNode(BaseNode[OrderGraphState]):
    """Regenerate derived profiles only after raw cargo has changed."""

    name = "cargo_profile"

    def __init__(self, model: CargoProfileModel):
        self.model = model

    def run(self, state: OrderGraphState) -> Dict[str, Any]:
        from ...cargo_profile.updater import regenerate_cargo_profile

        original = state["order_context"]
        updated = regenerate_cargo_profile(original, self.model)
        return {
            "order_context": updated,
            "cargo_profile_updated": updated != original,
        }


class FinalizeNode(BaseNode[OrderGraphState]):
    name = "finalize"

    def run(self, state: OrderGraphState) -> Dict[str, Any]:
        # Return only derived values; input history and order_context are never
        # mutated by this graph.
        return {
            "rewrite_result": state.get("rewrite_result"),
            "entities": list(state.get("entities", [])),
            "order_context": state.get("order_context"),
            "order_context_updated": state.get("order_context_updated", False),
            "cargo_profile_updated": state.get("cargo_profile_updated", False),
        }


__all__ = [
    "RewriteNode",
    "ExtractNode",
    "ContextUpdateNode",
    "CargoProfileNode",
    "FinalizeNode",
]
