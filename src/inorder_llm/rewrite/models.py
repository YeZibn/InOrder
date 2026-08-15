"""Models returned by the order rewrite stage."""

from dataclasses import dataclass
from typing import Any, Dict, Optional


@dataclass(frozen=True)
class RewriteResult:
    rewritten_text: str
    extraction_text: str
    needs_clarification: bool = False
    clarification_reason: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "rewritten_text": self.rewritten_text,
            "extraction_text": self.extraction_text,
            "needs_clarification": self.needs_clarification,
            "clarification_reason": self.clarification_reason,
        }


__all__ = ["RewriteResult"]
