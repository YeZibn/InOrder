from typing import Any, Dict

from ....graph.base import BaseNode
from ....intent.models import IntentPlan
from ....intent.planning import IntentModel, IntentPlanValidationError, _step_from_candidate, validate_plan


class MainIntentNode(BaseNode):
    name = "main_intent"

    def __init__(self, model: IntentModel):
        self.model = model

    def run(self, state) -> Dict[str, Any]:
        result = self.model.classify_main_intent(state["message"])
        main_intent = result.get("main_intent")
        if main_intent not in ("order", "qa", "ambiguous"):
            raise IntentPlanValidationError("invalid main_intent")
        update = {"main_intent": main_intent, "main_confidence": result.get("confidence")}
        if main_intent == "ambiguous":
            update.update(needs_clarification=True, clarification_reason="无法确定用户是要执行订单操作还是进行问答")
        return update


class SubIntentNode(BaseNode):
    name = "sub_intent"

    def __init__(self, model: IntentModel):
        self.model = model

    def run(self, state) -> Dict[str, Any]:
        if state.get("main_intent") != "order":
            raise IntentPlanValidationError("sub_intent_node requires order main_intent")
        candidates = self.model.extract_sub_intents(state["message"], "order")
        return {"sub_intents": [_step_from_candidate(dict(item), index + 1) for index, item in enumerate(candidates)]}


class BuildPlanNode(BaseNode):
    name = "build_plan"

    def run(self, state) -> Dict[str, Any]:
        main_intent = state["main_intent"]
        sub_intents = tuple(state.get("sub_intents", ()))
        needs = state.get("needs_clarification", False)
        reason = state.get("clarification_reason")
        if main_intent == "order" and not sub_intents:
            needs, reason = True, reason or "未识别出具体订单操作"
        plan = IntentPlan(main_intent, sub_intents, needs, reason, state.get("main_confidence"), state.get("message"))
        return {"intent_plan": plan, "needs_clarification": needs, "clarification_reason": reason}


class ValidatePlanNode(BaseNode):
    name = "validate_plan"

    def run(self, state):
        return {"intent_plan": validate_plan(state["intent_plan"])}


class ClarificationNode(BaseNode):
    name = "clarification"

    def run(self, state):
        return {"needs_clarification": True, "clarification_reason": state.get("clarification_reason") or "需要进一步澄清用户意图"}


class FinalizeNode(BaseNode):
    name = "finalize"

    def run(self, state):
        return {"intent_plan": state["intent_plan"]}
