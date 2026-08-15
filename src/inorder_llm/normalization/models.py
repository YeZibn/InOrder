"""Models and errors for deterministic order-value normalization."""

from dataclasses import dataclass
from typing import Any, Optional, Tuple


@dataclass(frozen=True)
class NormalizationError(ValueError):
    """Raised when an enum value cannot be normalized safely."""

    entity_type: str
    raw_value: Any
    supported_values: Tuple[Any, ...]
    reason: str = "unknown enum value"

    def __str__(self) -> str:
        return (
            f"{self.reason} for {self.entity_type}: {self.raw_value!r}; "
            f"supported values: {', '.join(map(str, self.supported_values))}"
        )


@dataclass(frozen=True)
class NormalizedValue:
    """A normalized value together with the original user expression."""

    value: Any
    raw: Any


__all__ = ["NormalizationError", "NormalizedValue"]
