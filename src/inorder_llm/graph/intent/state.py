from typing import Literal, Optional, TypedDict
from ...intent.models import IntentPlan

class IntentGraphState(TypedDict, total=False):
    message: str
    deadline_at: float
    main_intent: Literal["order", "qa"]
    main_confidence: Optional[float]
    intent_plan: IntentPlan
