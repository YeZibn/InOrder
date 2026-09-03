from dataclasses import dataclass, field
from typing import Any, Dict, Optional


@dataclass(frozen=True)
class IntentPlan:
    main_intent: str
    confidence: Optional[float] = None
    raw_message: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {"main_intent": self.main_intent, "confidence": self.confidence, "raw_message": self.raw_message}


__all__ = ["IntentPlan"]
