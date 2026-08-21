"""Production vehicle normalization using exact match then strict ensemble."""

from copy import deepcopy

from ..catalog import find_vehicle_keyword, iter_vehicle_keywords
from ..extract.models import Entity
from ..vehicle_matching import EnsembleMatcher


_VEHICLE_TYPES = {"vehicle_type", "vehicle_specs"}


def _input_value(entity: Entity):
    return entity.attributes.get("value", entity.attributes.get("extraction_text", entity.extraction_text))


def normalize_vehicle_entity(entity: Entity) -> Entity:
    """Normalize a vehicle entity without guessing across entity types.

    Exact catalog matches win.  Fuzzy matching is attempted only after an
    exact miss and must pass the RapidFuzz/n-gram ensemble guards.
    """
    if entity.type not in _VEHICLE_TYPES:
        return entity
    raw = _input_value(entity)
    attrs = deepcopy(dict(entity.attributes))
    exact = find_vehicle_keyword(raw, entity.type)
    if exact is None:
        exact = next((item for item in iter_vehicle_keywords() if item.entity_type == entity.type and item.code == raw), None)
    if exact is not None:
        attrs.update({"value": exact.code, "raw": raw, "normalization_method": "exact", "normalization_accepted": True})
        return Entity(entity.type, entity.action, attrs, entity.extraction_text)

    result = EnsembleMatcher().match(str(raw), entity.type)
    attrs.update({
        "value": result.candidate_code if result.accepted else raw,
        "raw": raw,
        "normalization_method": result.method,
        "normalization_accepted": result.accepted,
        "normalization_reason": result.reason,
        "normalization_score": result.score,
    })
    return Entity(entity.type, entity.action, attrs, entity.extraction_text)


__all__ = ["normalize_vehicle_entity"]
