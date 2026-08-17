from dataclasses import dataclass, field
from typing import Any, Dict, Literal, Mapping, Optional

Action = Literal["add", "set", "remove", "replace"]


@dataclass(frozen=True)
class Entity:
    type: str
    action: Action
    attributes: Mapping[str, Any] = field(default_factory=dict)
    extraction_text: str = ""

    def to_dict(self) -> Dict[str, Any]:
        result: Dict[str, Any] = {
            "type": self.type,
            "action": self.action,
            "attributes": dict(self.attributes),
        }
        if self.extraction_text:
            result["extraction_text"] = self.extraction_text
        return result


@dataclass(frozen=True)
class GroundedExtraction:
    """Backend-neutral grounded extraction preserving source evidence."""

    extraction_class: str
    extraction_text: str
    attributes: Mapping[str, Any] = field(default_factory=dict)
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "extraction_class": self.extraction_class,
            "extraction_text": self.extraction_text,
            "attributes": dict(self.attributes),
            "metadata": dict(self.metadata),
        }


__all__ = ["Entity", "GroundedExtraction", "Action"]
