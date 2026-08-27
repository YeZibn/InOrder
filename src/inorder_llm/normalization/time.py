"""Deterministic normalization for extracted time entities."""

from copy import deepcopy
from datetime import datetime, timezone
from typing import Any, Iterable, List, Optional
from zoneinfo import ZoneInfo

from ..extract.models import Entity


TIMEZONE = ZoneInfo("Asia/Shanghai")
TIME_FORMATS = ("%Y-%m-%d %H:%M", "%Y-%m-%d %H:%M:%S")


class TimeNormalizationError(ValueError):
    """Raised when extracted time boundaries cannot be normalized safely."""

    def __init__(self, message: str, *, field: Optional[str] = None, value: Any = None):
        super().__init__(message)
        self.field = field
        self.value = value


def _parse_boundary(value: Any, field: str) -> Optional[datetime]:
    if value is None or value == "":
        return None
    if not isinstance(value, str):
        raise TimeNormalizationError(f"{field} must be a datetime string", field=field, value=value)
    text = value.strip()
    parsed: Optional[datetime] = None
    for fmt in TIME_FORMATS:
        try:
            parsed = datetime.strptime(text, fmt)
            break
        except ValueError:
            continue
    if parsed is None:
        try:
            parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
        except ValueError as exc:
            raise TimeNormalizationError(
                f"{field} has invalid datetime format", field=field, value=value
            ) from exc
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=TIMEZONE)
    return parsed.astimezone(TIMEZONE)


def _format_boundary(value: Optional[datetime]) -> Optional[str]:
    return value.isoformat(timespec="seconds") if value is not None else None


def normalize_time_entity(entity: Entity) -> Entity:
    """Return a normalized time entity without mutating the input entity."""
    if entity.type != "time":
        return entity
    attrs = deepcopy(dict(entity.attributes))
    start = _parse_boundary(attrs.get("start"), "start")
    end = _parse_boundary(attrs.get("end"), "end")
    if start is None and end is None:
        raise TimeNormalizationError("time requires at least one boundary")
    if start is not None and end is not None and start > end:
        raise TimeNormalizationError("time start must not be later than end")
    kind = "fixed" if start is not None and end is not None and start == end else "range"
    raw = attrs.get("raw", entity.extraction_text)
    attrs.update(
        {
            "start": _format_boundary(start),
            "end": _format_boundary(end),
            "kind": kind,
            "timezone": "Asia/Shanghai",
            "raw": raw,
        }
    )
    return Entity(entity.type, entity.action, attrs, entity.extraction_text)


def normalize_time_entities(entities: Iterable[Entity]) -> List[Entity]:
    return [normalize_time_entity(entity) for entity in entities]


__all__ = [
    "TimeNormalizationError",
    "normalize_time_entity",
    "normalize_time_entities",
]
