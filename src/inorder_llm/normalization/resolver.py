"""Pure normalization for order enum entities."""

from copy import deepcopy
from typing import Any, Iterable, List, Mapping

from ..extract.models import Entity
from .enums import CANONICAL_VALUES, ENUM_ALIASES
from .models import NormalizationError


_ENTITY_TO_FIELD = {
    "payment_type": "payment_type",
    "invoice_type": "invoice_type",
    "oneself_follow_flag": "oneself_follow_flag",
}


def _clean(value: Any) -> Any:
    if not isinstance(value, str):
        return value
    return "".join(value.strip().split()).replace("：", ":")


def _value_for_normalization(entity: Entity) -> Any:
    attrs = entity.attributes
    if "value" in attrs:
        return attrs["value"]
    if "extraction_text" in attrs:
        return attrs["extraction_text"]
    return entity.extraction_text


def _raw_expression(entity: Entity, value: Any) -> Any:
    return entity.attributes.get("raw", value)


def _normalize_value(field: str, entity_type: str, raw: Any) -> Any:
    cleaned = _clean(raw)
    canonical = CANONICAL_VALUES[field]
    if field != "service_type" and isinstance(cleaned, bool):
        raise NormalizationError(entity_type, raw, canonical, "invalid enum type")
    if cleaned in canonical:
        return cleaned
    if isinstance(cleaned, str):
        aliases = ENUM_ALIASES[field]
        if cleaned in aliases:
            return aliases[cleaned]
        lowered = cleaned.lower()
        for alias, value in aliases.items():
            if alias.lower() == lowered:
                return value
    raise NormalizationError(entity_type, raw, canonical)


def normalize_entity(entity: Entity) -> Entity:
    """Return a normalized copy; non-enum entities pass through unchanged."""
    field = _ENTITY_TO_FIELD.get(entity.type, entity.type if entity.type == "service_type" else None)
    if field is None:
        return entity
    value_input = _value_for_normalization(entity)
    value = _normalize_value(field, entity.type, value_input)
    raw = _raw_expression(entity, value_input)
    attrs = deepcopy(dict(entity.attributes))
    attrs["value"] = value
    attrs["raw"] = raw
    return Entity(entity.type, entity.action, attrs, entity.extraction_text)


def normalize_entities(entities: Iterable[Entity]) -> List[Entity]:
    """Normalize entities without mutating the iterable or its members."""
    return [normalize_entity(entity) for entity in entities]


__all__ = ["normalize_entity", "normalize_entities"]
