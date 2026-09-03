from typing import Any, Mapping, Protocol


class IntentModel(Protocol):
    def classify_main_intent(self, message: str) -> Mapping[str, Any]: ...

__all__ = ["IntentModel"]
