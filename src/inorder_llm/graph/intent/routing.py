from typing import Literal

from .state import IntentGraphState


def route_main_intent(state: IntentGraphState) -> Literal["order", "qa", "ambiguous"]:
    return state["main_intent"]
