from typing import Literal

from .state import MainGraphState


def route_main_graph(state: MainGraphState) -> Literal["order", "qa"]:
    return "order" if state.get("main_intent") == "order" else "qa"


__all__ = ["route_main_graph"]
