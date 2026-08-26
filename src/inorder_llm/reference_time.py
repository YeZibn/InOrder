"""Request-scoped reference time helpers.

The reference time is an input anchor for relative time expressions.  It is
resolved once at a request boundary and then passed explicitly through the
workflow rather than being read by individual nodes.
"""

from datetime import datetime
from typing import Optional
from zoneinfo import ZoneInfo


TIMEZONE = ZoneInfo("Asia/Shanghai")
TIME_FORMAT = "%Y-%m-%d %H:%M"


class ReferenceTimeError(ValueError):
    """Raised when a supplied reference time is not valid."""


def current_reference_time() -> str:
    """Return the current Shanghai time in the public wire format."""

    return datetime.now(TIMEZONE).strftime(TIME_FORMAT)


def resolve_reference_time(value: Optional[str]) -> str:
    """Validate a caller value or generate one default for this request.

    Empty values are treated as omitted.  The returned string is intentionally
    timezone-free because the existing prompt contract carries the timezone
    separately as the Asia/Shanghai request convention.
    """

    if value is None or not str(value).strip():
        return current_reference_time()
    candidate = str(value).strip()
    try:
        datetime.strptime(candidate, TIME_FORMAT)
    except ValueError as exc:
        raise ReferenceTimeError(
            "reference_time must use format YYYY-MM-DD HH:MM"
        ) from exc
    return candidate


def resolve_context_reference_time(
    context_value: Optional[str], request_value: Optional[str] = None
) -> str:
    """Resolve a conversation anchor, preferring a persisted context value."""

    if context_value is not None and str(context_value).strip():
        return resolve_reference_time(context_value)
    return resolve_reference_time(request_value)


__all__ = [
    "TIMEZONE", "TIME_FORMAT", "ReferenceTimeError", "current_reference_time",
    "resolve_reference_time", "resolve_context_reference_time",
]
