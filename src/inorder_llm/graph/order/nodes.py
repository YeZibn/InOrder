"""Nodes for the standalone order-processing subgraph."""

import inspect
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
        context = state["order_context"]
        entities = state.get("entities", [])
        vehicle_entities = [entity for entity in normalize_entities(entities) if entity.type in ("vehicle_type", "vehicle_specs")]
        unresolved = [entity for entity in vehicle_entities if entity.attributes.get("normalization_accepted") is False]
        matched_specs = [
            entity.attributes["value"]
            for entity in vehicle_entities
            if entity.type == "vehicle_specs"
            and entity.attributes.get("normalization_accepted") is not False
            and isinstance(entity.attributes.get("value"), str)
        ]
        has_matched_user_vehicle = bool(context.vehicle_type) and not unresolved and (
            bool(vehicle_entities) or context.vehicle_source in (None, "user_matched")
        )
        if has_matched_user_vehicle:
            from ...catalog import get_vehicle_type
            specs = list(context.vehicle_specs)
            type_record = get_vehicle_type(context.vehicle_type)
            label = type_record.label if type_record else context.vehicle_type
            return {
                "vehicle_resolution": VehicleResolutionResult(
                    context.vehicle_type, specs, "user_matched",
                    f"采用用户指定车型：{label}",
                )
            }
        raw_text = unresolved[0].extraction_text if unresolved else None
        pickup = context.pickup_location if isinstance(context.pickup_location, dict) else {}
        user_location = state.get("user_location") or {}
        effective_city = pickup.get("city") or user_location.get("city")
        parameters = inspect.signature(self.model.resolve).parameters.values()
        if any(p.name == "effective_city" or p.kind is inspect.Parameter.VAR_KEYWORD for p in parameters):
            result = self.model.resolve(context.cargo_profiles, context.cargo_profile_summary, raw_text, effective_city=effective_city)
        else:
            result = self.model.resolve(context.cargo_profiles, context.cargo_profile_summary, raw_text)
        if matched_specs:
            merged_specs = list(dict.fromkeys([*result.vehicle_specs, *matched_specs]))
            result = replace(result, vehicle_specs=merged_specs)
        from copy import deepcopy
        updated = deepcopy(context)
        lower_bound_primary = next(
            (
                candidate
                for candidate in result.candidates
                if candidate.get("fit_level") == "lower_bound_fit"
            ),
            None,
        ) if result.source == "estimated" else None
        if lower_bound_primary is not None:
            primary_type = lower_bound_primary.get("vehicle_type")
            if isinstance(primary_type, str) and primary_type:
                primary_specs = list(lower_bound_primary.get("vehicle_specs", result.vehicle_specs))
                if matched_specs:
                    primary_specs = list(dict.fromkeys([*primary_specs, *matched_specs]))
                result = replace(
                    result,
                    vehicle_type=primary_type,
                    vehicle_specs=primary_specs,
                )
                updated.vehicle_type = result.vehicle_type
                updated.vehicle_specs = list(result.vehicle_specs)
                updated.vehicle_source = "estimated"
        else:
            if result.source == "estimated" and result.vehicle_type:
                result = replace(result, vehicle_type="")
            if matched_specs:
                updated.vehicle_specs = list(dict.fromkeys([*updated.vehicle_specs, *matched_specs]))
        return {"vehicle_resolution": result, "order_context": updated, "order_context_updated": updated != context}


__all__ = [
    "RewriteNode",
    "ExtractNode",
    "ContextUpdateNode",
    "CargoProfileNode",
    "VehicleResolutionNode",
    "OrderCompletenessNode",
    "FinalizeNode",
]
