"""Models returned by the order rewrite stage."""

from dataclasses import dataclass
from typing import Any, Dict


@dataclass(frozen=True)
class RewriteResult:
    rewritten_text: str
    extraction_text: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "rewritten_text": self.rewritten_text,
            "extraction_text": self.extraction_text,
        }


__all__ = ["RewriteResult"]
