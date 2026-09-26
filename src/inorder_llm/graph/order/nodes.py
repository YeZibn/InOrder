"""Nodes for the standalone order-processing subgraph."""

import inspect
from copy import deepcopy
from dataclasses import replace
from typing import Any, Dict, Literal

from ...graph.base import BaseNode
from ...context import OrderContextReducer
from .protocols import CargoProfileModel, EntityExtractorModel, RewriteModel
from .protocols import VehicleResolutionModel
from ...normalization import normalize_entities
from ...vehicle_resolution.models import VehicleResolutionResult
from ...order_summary import check_order_completeness
from .state import OrderGraphState


def _entity_action(entity) -> str:
    action = entity.attributes.get("action")
    return action if action in ("add", "set", "remove", "replace") else entity.action


class RewriteNode(BaseNode[OrderGraphState]):
    name = "rewrite"

    def __init__(self, model: RewriteModel):
        self.model = model

    def run(self, state: OrderGraphState) -> Dict[str, Any]:
        # Keep compatibility with injected legacy implementations while making
        # the request-scoped anchor explicit for production resolvers. Inspect
        # the signature instead of catching TypeError from inside the model.
        parameters = inspect.signature(self.model.rewrite).parameters.values()
        accepts_reference_time = any(
            parameter.name == "reference_time"
            or parameter.kind is inspect.Parameter.VAR_KEYWORD
            for parameter in parameters
        )
        if accepts_reference_time:
            result = self.model.rewrite(
                state["message"], state["history"], state["order_context"],
                reference_time=state.get("reference_time"),
            )
        else:
            result = self.model.rewrite(
                state["message"], state["history"], state["order_context"]
            )
        return {
            "rewrite_result": result,
        }

    def supports_async(self) -> bool:
        return callable(getattr(self.model, "arewrite", None))

    async def arun(self, state: OrderGraphState) -> Dict[str, Any]:
        result = await self.model.arewrite(
            state["message"], state["history"], state["order_context"],
            reference_time=state.get("reference_time"), deadline_at=state.get("deadline_at"),
        )
        return {"rewrite_result": result}


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

    def supports_async(self) -> bool:
        return callable(getattr(self.extractor, "aextract", None))

    async def arun(self, state: OrderGraphState) -> Dict[str, Any]:
        entities = await self.extractor.aextract(
            state["rewrite_result"].extraction_text, state["reference_time"],
            deadline_at=state.get("deadline_at"),
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
        user_location = state.get("user_location") or {}

        def effective_city(context):
            pickup = context.pickup_location if isinstance(context.pickup_location, dict) else {}
            return pickup.get("city") or user_location.get("city")

        return {
            "order_context": updated,
            "order_context_updated": updated != original,
            "cargo_updated": updated.cargo != original.cargo,
            "vehicle_estimate_inputs_changed": (
                updated.cargo != original.cargo
                or effective_city(updated) != effective_city(original)
                or updated.vehicle_specs != original.vehicle_specs
            ),
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

    def supports_async(self) -> bool:
        return callable(getattr(self.model, "aprofile", None))

    async def arun(self, state: OrderGraphState) -> Dict[str, Any]:
        from copy import deepcopy
        original = state["order_context"]
        updated = deepcopy(original)
        if not original.cargo:
            updated.cargo_profiles = []
            updated.cargo_profile_summary = None
            return {"order_context": updated, "cargo_profile_updated": updated != original}
        result = await self.model.aprofile(deepcopy(original.cargo), deadline_at=state.get("deadline_at"))
        payload = result.to_dict() if hasattr(result, "to_dict") else result
        updated.cargo_profiles = deepcopy(payload["cargo_profiles"])
        updated.cargo_profile_summary = deepcopy(payload["cargo_profile_summary"])
        return {"order_context": updated, "cargo_profile_updated": updated != original}


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
            "vehicle_resolution": state.get("vehicle_resolution"),
            "order_summary": state.get("order_summary"),
        }


class OrderCompletenessNode(BaseNode[OrderGraphState]):
    """Build the final deterministic business summary from the final context."""

    name = "order_completeness"

    def run(self, state: OrderGraphState) -> Dict[str, Any]:
        summary = check_order_completeness(
            state["order_context"], state.get("vehicle_resolution")
        )
        return {"order_summary": summary}


class VehicleResolutionNode(BaseNode[OrderGraphState]):
    name = "vehicle_resolution"

    def __init__(self, model: VehicleResolutionModel):
        self.model = model

    def run(self, state: OrderGraphState) -> Dict[str, Any]:
        original_context = state["order_context"]
        context = deepcopy(original_context)
        entities = state.get("entities", [])
        vehicle_entities = [entity for entity in normalize_entities(entities) if entity.type in ("vehicle_type", "vehicle_specs")]
        unresolved_types = [
            entity for entity in vehicle_entities
            if entity.type == "vehicle_type" and entity.attributes.get("normalization_accepted") is False
        ]
        if context.vehicle_type and context.vehicle_source is None:
            # Compatibility for legacy contexts with a canonical vehicle but
            # no provenance; OrderContextReducer applies the same rule.
            context.vehicle_source = "user_matched"
        if not context.vehicle_type:
            context.vehicle_source = None

        if context.vehicle_type and context.vehicle_source == "user_matched":
            raw_text = unresolved_types[0].extraction_text if unresolved_types else None
            reason = "采用用户指定车型。"
            if raw_text:
                reason += f"本轮车型表达“{raw_text}”未能唯一匹配，因此保留当前用户选择。"
            return {
                "vehicle_resolution": VehicleResolutionResult(
                    context.vehicle_type,
                    list(context.vehicle_specs),
                    "user_matched",
                    reason,
                    raw_vehicle_text=raw_text,
                ),
                "order_context": context,
                "order_context_updated": context != original_context,
            }

        raw_text = unresolved_types[0].extraction_text if unresolved_types else None
        if (
            context.vehicle_type
            and unresolved_types
            and _entity_action(unresolved_types[0]) != "replace"
            and not state.get("vehicle_estimate_inputs_changed", False)
        ):
            return {
                "vehicle_resolution": VehicleResolutionResult(
                    context.vehicle_type,
                    list(context.vehicle_specs),
                    "estimated",
                    "保留当前估算车型；本轮无法匹配的表达未明确要求替换。",
                    raw_vehicle_text=raw_text,
                ),
                "order_context": context,
                "order_context_updated": context != original_context,
            }
        pickup = context.pickup_location if isinstance(context.pickup_location, dict) else {}
        user_location = state.get("user_location") or {}
        effective_city = pickup.get("city") or user_location.get("city")
        parameters = inspect.signature(self.model.resolve).parameters
        accepts_kwargs = any(
            parameter.kind is inspect.Parameter.VAR_KEYWORD
            for parameter in parameters.values()
        )
        kwargs = {}
        if "effective_city" in parameters or accepts_kwargs:
            kwargs["effective_city"] = effective_city
        if "vehicle_specs" in parameters or accepts_kwargs:
            kwargs["vehicle_specs"] = list(context.vehicle_specs)
        result = self.model.resolve(
            context.cargo_profiles,
            context.cargo_profile_summary,
            raw_text,
            **kwargs,
        )

        def merge_specs(*groups):
            return list(dict.fromkeys(
                item for group in groups for item in group
                if isinstance(item, str) and item
            ))

        # Keep user-provided specifications in every result, including legacy
        # injected resolvers that do not accept the optional argument yet.
        result_specs = merge_specs(result.vehicle_specs, context.vehicle_specs)
        candidates = []
        for candidate in result.candidates:
            item = dict(candidate)
            item["vehicle_specs"] = merge_specs(item.get("vehicle_specs", []), context.vehicle_specs)
            candidates.append(item)
        result = replace(result, vehicle_specs=result_specs, candidates=candidates)

        updated = deepcopy(context)
        lower_bound_primary = next(
            (
                candidate
                for candidate in result.candidates
                if candidate.get("fit_level") == "lower_bound_fit"
            ),
            None,
        ) if result.source == "estimated" else None
        primary_type = lower_bound_primary.get("vehicle_type") if lower_bound_primary else None
        if isinstance(primary_type, str) and primary_type:
            result = replace(
                result,
                vehicle_type=primary_type,
                vehicle_specs=list(lower_bound_primary.get("vehicle_specs", result.vehicle_specs)),
            )
            updated.vehicle_type = primary_type
            updated.vehicle_source = "estimated"
        else:
            if result.source == "estimated":
                result = replace(result, vehicle_type="")
                if updated.vehicle_source == "estimated":
                    updated.vehicle_type = None
                    updated.vehicle_source = None
            if not updated.vehicle_type:
                updated.vehicle_source = None

        return {"vehicle_resolution": result, "order_context": updated, "order_context_updated": updated != original_context}


__all__ = [
    "RewriteNode",
    "ExtractNode",
    "ContextUpdateNode",
    "CargoProfileNode",
    "VehicleResolutionNode",
    "OrderCompletenessNode",
    "FinalizeNode",
]
