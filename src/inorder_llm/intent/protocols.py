from typing import Any, Mapping, Protocol, Sequence


class IntentModel(Protocol):
    def classify_main_intent(self, message: str) -> Mapping[str, Any]: ...
    def extract_sub_intents(self, message: str, main_intent: str) -> Sequence[Mapping[str, Any]]: ...

__all__ = ["IntentModel"]
