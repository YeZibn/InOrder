"""Nodes for the standalone order-processing subgraph."""

from typing import Any, Dict, Literal

from ...graph.base import BaseNode
from .protocols import EntityExtractorModel, RewriteModel
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
            "needs_clarification": result.needs_clarification,
            "clarification_reason": result.clarification_reason,
        }


def route_rewrite(state: OrderGraphState) -> Literal["clarification", "extract"]:
    return "clarification" if state.get("needs_clarification") else "extract"


class ExtractNode(BaseNode[OrderGraphState]):
    name = "extract"

    def __init__(self, extractor: EntityExtractorModel):
        self.extractor = extractor

    def run(self, state: OrderGraphState) -> Dict[str, Any]:
        rewrite_result = state["rewrite_result"]
        entities = self.extractor.extract(
            rewrite_result.extraction_text,
            state["history"].as_llm_messages(),
            state["reference_time"],
        )
        return {"entities": entities}


class ClarificationNode(BaseNode[OrderGraphState]):
    name = "clarification"

    def run(self, state: OrderGraphState) -> Dict[str, Any]:
        return {"entities": []}


class FinalizeNode(BaseNode[OrderGraphState]):
    name = "finalize"

    def run(self, state: OrderGraphState) -> Dict[str, Any]:
        # Return only derived values; history and order_context are never
        # mutated by this graph.
        return {
            "rewrite_result": state.get("rewrite_result"),
            "entities": list(state.get("entities", [])),
            "needs_clarification": state.get("needs_clarification", False),
            "clarification_reason": state.get("clarification_reason"),
        }


__all__ = [
    "RewriteNode",
    "ExtractNode",
    "ClarificationNode",
    "FinalizeNode",
    "route_rewrite",
]
