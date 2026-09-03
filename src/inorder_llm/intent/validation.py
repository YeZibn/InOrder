from .models import IntentPlan
from .resolver import IntentPlanningError

MAIN_INTENTS = frozenset(("order", "qa"))


class IntentPlanValidationError(IntentPlanningError):
    pass


def validate_plan(plan: IntentPlan) -> IntentPlan:
    if plan.main_intent not in MAIN_INTENTS:
        raise IntentPlanValidationError("invalid main_intent: " + str(plan.main_intent))
    if plan.confidence is not None and not 0 <= plan.confidence <= 1:
        raise IntentPlanValidationError("confidence must be between 0 and 1")
    return plan


__all__ = ["MAIN_INTENTS", "IntentPlanningError", "IntentPlanValidationError", "validate_plan"]
