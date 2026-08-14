from typing import Any, Dict, Mapping
from .models import IntentPlan, IntentStep
from .resolver import IntentPlanningError

MAIN_INTENTS = frozenset(("order", "qa"))
ORDER_SUB_INTENTS = frozenset(("create_order", "modify_draft", "query_history_order"))


class IntentPlanValidationError(IntentPlanningError):
    pass


def _step_from_candidate(candidate: Mapping[str, Any], index: int) -> IntentStep:
    name = candidate.get("name")
    if not isinstance(name, str):
        raise IntentPlanValidationError("each sub-intent requires a name")
    depends_on = candidate.get("depends_on", ())
    if isinstance(depends_on, str): depends_on = (depends_on,)
    if not isinstance(depends_on, (list, tuple)):
        raise IntentPlanValidationError("depends_on must be an array")
    arguments = candidate.get("arguments", {})
    if not isinstance(arguments, dict):
        raise IntentPlanValidationError("arguments must be an object")
    return IntentStep(candidate.get("id", "step_" + str(index)), name, arguments, tuple(depends_on))


def validate_plan(plan: IntentPlan) -> IntentPlan:
    if plan.main_intent not in MAIN_INTENTS: raise IntentPlanValidationError("invalid main_intent: " + str(plan.main_intent))
    if plan.main_intent != "order" and plan.sub_intents: raise IntentPlanValidationError("only order intent may contain order sub-intents")
    ids = [step.id for step in plan.sub_intents]
    if len(ids) != len(set(ids)): raise IntentPlanValidationError("intent step ids must be unique")
    if any(step.name not in ORDER_SUB_INTENTS for step in plan.sub_intents): raise IntentPlanValidationError("invalid order sub-intent")
    known = set(ids)
    for step in plan.sub_intents:
        if step.id in step.depends_on or any(dep not in known for dep in step.depends_on): raise IntentPlanValidationError("intent dependencies must reference other steps")
    visiting, visited = set(), set()
    def visit(step_id):
        if step_id in visiting: raise IntentPlanValidationError("intent dependencies must be acyclic")
        if step_id in visited: return
        visiting.add(step_id)
        step = next(step for step in plan.sub_intents if step.id == step_id)
        for dependency in step.depends_on: visit(dependency)
        visiting.remove(step_id); visited.add(step_id)
    for step_id in ids: visit(step_id)
    if plan.needs_clarification and not plan.clarification_reason: raise IntentPlanValidationError("clarification_reason is required when clarification is needed")
    return plan

__all__ = ["MAIN_INTENTS", "ORDER_SUB_INTENTS", "IntentPlanningError", "IntentPlanValidationError", "validate_plan"]
