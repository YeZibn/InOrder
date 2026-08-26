"""Stable, JSON-compatible contract for order completeness results."""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Mapping


@dataclass(frozen=True)
class MissingOrderField:
    field: str
    label: str
    reason: str = ""

    def to_dict(self) -> Dict[str, str]:
        result = {"field": self.field, "label": self.label}
        if self.reason:
            result["reason"] = self.reason
        return result


@dataclass(frozen=True)
class OrderSummary:
    status: str
    summary: str
    facts: Mapping[str, Any] = field(default_factory=dict)
    missing_required: List[MissingOrderField] = field(default_factory=list)
    missing_optional: List[MissingOrderField] = field(default_factory=list)
    next_prompt: str = ""
    user_message: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "status": self.status,
            "summary": self.summary,
            "user_message": self.user_message,
            "facts": dict(self.facts),
            "missing_required": [item.to_dict() for item in self.missing_required],
            "missing_optional": [item.to_dict() for item in self.missing_optional],
            "next_prompt": self.next_prompt,
        }
