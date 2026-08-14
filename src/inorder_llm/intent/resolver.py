import json
from typing import Any, Mapping, Sequence

from ..infrastructure.llm import ChatMessage, LLMClient
from .protocols import IntentModel


class IntentPlanningError(Exception):
    """Base error for intent recognition and plan validation."""


class StructuredIntentError(IntentPlanningError):
    pass


class LLMIntentModel:
    def __init__(self, client: LLMClient):
        self.client = client

    def _json_call(self, instruction: str) -> Mapping[str, Any]:
        response = self.client.chat([ChatMessage("system", instruction)])
        try:
            value = json.loads(response.text)
        except (TypeError, ValueError) as exc:
            raise StructuredIntentError("LLM returned invalid intent JSON") from exc
        if not isinstance(value, dict):
            raise StructuredIntentError("LLM intent output must be a JSON object")
        return value

    def classify_main_intent(self, message: str) -> Mapping[str, Any]:
        return self._json_call("Classify the user's message. Return JSON only with keys main_intent (order, qa, ambiguous) and confidence. Message: " + message)

    def extract_sub_intents(self, message: str, main_intent: str) -> Sequence[Mapping[str, Any]]:
        value = self._json_call("Extract zero or more order sub-intents. Return JSON only with key sub_intents, an array of objects with name, arguments, and optional depends_on. Allowed names: create_order, modify_draft, query_history_order. Message: " + message)
        items = value.get("sub_intents", [])
        if not isinstance(items, list):
            raise StructuredIntentError("sub_intents must be an array")
        return items

__all__ = ["LLMIntentModel", "StructuredIntentError"]
