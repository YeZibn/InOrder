from .models import IntentPlan, IntentPlanningState
from .protocols import IntentModel
from .resolver import IntentPlanningError
from .validation import IntentPlanValidationError, _step_from_candidate, validate_plan


class IntentPlanningSubgraph:
    def __init__(self, model: IntentModel): self.model = model
    def classify_main_intent(self, state):
        result = self.model.classify_main_intent(state.message); state.main_intent = result.get("main_intent"); state.confidence = result.get("confidence")
        if state.main_intent not in ("order", "qa", "ambiguous"): raise IntentPlanValidationError("invalid main_intent")
        if state.main_intent == "ambiguous": state.needs_clarification = True; state.clarification_reason = "无法确定用户是要执行订单操作还是进行问答"
        return state
    def extract_sub_intents(self, state):
        if state.main_intent == "order": state.candidates = [dict(item) for item in self.model.extract_sub_intents(state.message, state.main_intent)]
        return state
    def normalize_sub_intents(self, state):
        state.sub_intents = [_step_from_candidate(item, i + 1) for i, item in enumerate(state.candidates)]; return state
    def build_intent_plan(self, state):
        if state.main_intent == "order" and not state.sub_intents: state.needs_clarification = True; state.clarification_reason = state.clarification_reason or "未识别出具体订单操作"
        state.plan = IntentPlan(state.main_intent, tuple(state.sub_intents), state.needs_clarification, state.clarification_reason, state.confidence, state.message); return state
    def validate_intent_plan(self, state): state.plan = validate_plan(state.plan); return state
    def invoke(self, message):
        state = IntentPlanningState(message=message)
        for node in (self.classify_main_intent, self.extract_sub_intents, self.normalize_sub_intents, self.build_intent_plan, self.validate_intent_plan): state = node(state)
        return state.plan


def build_intent_planning_subgraph(model): return IntentPlanningSubgraph(model)

__all__ = ["IntentPlanningSubgraph", "build_intent_planning_subgraph", "IntentModel", "IntentPlanValidationError", "IntentPlanningError", "_step_from_candidate", "validate_plan"]
