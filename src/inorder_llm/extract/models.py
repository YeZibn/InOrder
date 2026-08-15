from dataclasses import dataclass, field
from typing import Any, Dict, Literal, Mapping

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


__all__ = ["Entity", "Action"]
