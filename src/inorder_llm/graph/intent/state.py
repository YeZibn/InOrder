from typing import List, Literal, Optional, TypedDict

from ...intent.models import IntentPlan, IntentStep


class IntentGraphState(TypedDict, total=False):
    message: str
    main_intent: Literal["order", "qa"]
    main_confidence: Optional[float]
    sub_intents: List[IntentStep]
    intent_plan: IntentPlan
    needs_clarification: bool
    clarification_reason: Optional[str]
