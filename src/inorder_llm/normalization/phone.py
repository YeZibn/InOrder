"""Deterministic normalization for mainland mobile phone entities."""

from copy import deepcopy
import re
from typing import Any, Iterable, List

from ..extract.models import Entity


MAINLAND_MOBILE_PATTERN = re.compile(r"^1[3-9]\d{9}$")
_SEPARATORS = " -\u2010\u2011\u2012\u2013\u2014\u2212()（）"


class PhoneNormalizationError(ValueError):
    """Raised when a phone value is not a supported mainland mobile number."""

    def __init__(self, raw_value: Any, reason: str = "invalid mainland mobile number"):
        self.entity_type = "phone"
        self.raw_value = raw_value
        self.reason = reason
        super().__init__(f"{reason}: {raw_value!r}")


def _raw_value(entity: Entity) -> Any:
    attrs = entity.attributes
    return attrs.get("value", entity.extraction_text)


def _clean_phone(raw: Any) -> str:
    if not isinstance(raw, str):
        raise PhoneNormalizationError(raw, "phone value must be a string")
    value = raw.strip()
    # Separators are formatting only; all other non-digits remain invalid.
    value = "".join(char for char in value if char not in _SEPARATORS)
    if value.startswith("+86"):
        value = value[3:]
    elif value.startswith("0086"):
        value = value[4:]
    return value


def normalize_phone_entity(entity: Entity) -> Entity:
    """Return a normalized phone entity without mutating the input."""
    if entity.type != "phone":
        return entity
    value_input = _raw_value(entity)
    value = _clean_phone(value_input)
    if not MAINLAND_MOBILE_PATTERN.fullmatch(value):
        raise PhoneNormalizationError(value_input)
    attrs = deepcopy(dict(entity.attributes))
    attrs["value"] = value
    attrs["raw"] = attrs.get("raw", value_input)
    return Entity(entity.type, entity.action, attrs, entity.extraction_text)


def normalize_phone_entities(entities: Iterable[Entity]) -> List[Entity]:
    return [normalize_phone_entity(entity) for entity in entities]


__all__ = [
    "MAINLAND_MOBILE_PATTERN",
    "PhoneNormalizationError",
    "normalize_phone_entity",
    "normalize_phone_entities",
]
