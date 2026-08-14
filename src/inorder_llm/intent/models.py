from dataclasses import dataclass, field
from typing import Any, Dict, Mapping, Optional, Sequence


@dataclass(frozen=True)
class IntentStep:
    id: str
    name: str
    arguments: Mapping[str, Any] = field(default_factory=dict)
    depends_on: Sequence[str] = field(default_factory=tuple)

    def to_dict(self) -> Dict[str, Any]:
        result = {"id": self.id, "name": self.name, "arguments": dict(self.arguments)}
        if self.depends_on:
            result["depends_on"] = list(self.depends_on)
        return result


@dataclass(frozen=True)
class IntentPlan:
    main_intent: str
    sub_intents: Sequence[IntentStep] = field(default_factory=tuple)
    needs_clarification: bool = False
    clarification_reason: Optional[str] = None
    confidence: Optional[float] = None
    raw_message: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {"main_intent": self.main_intent, "sub_intents": [step.to_dict() for step in self.sub_intents], "needs_clarification": self.needs_clarification, "clarification_reason": self.clarification_reason, "confidence": self.confidence, "raw_message": self.raw_message}


__all__ = ["IntentPlan", "IntentStep"]
