from typing import Any, Dict

from ....graph.base import BaseNode
from ....intent.models import IntentPlan
from ....intent.protocols import IntentModel
from ....intent.validation import IntentPlanValidationError


class MainIntentNode(BaseNode):
    name = "main_intent"

    def __init__(self, model: IntentModel):
        self.model = model

    def run(self, state) -> Dict[str, Any]:
        result = self.model.classify_main_intent(state["message"])
        main_intent = result.get("main_intent")
        if main_intent not in ("order", "qa"):
            raise IntentPlanValidationError("invalid main_intent")
        return {"main_intent": main_intent, "main_confidence": result.get("confidence")}


class FinalizeNode(BaseNode):
    name = "finalize"

    def run(self, state):
        plan = IntentPlan(state["main_intent"], state.get("main_confidence"), state.get("message"))
        return {
            "main_intent": state["main_intent"],
            "main_confidence": state.get("main_confidence"),
            "intent_plan": plan,
        }
