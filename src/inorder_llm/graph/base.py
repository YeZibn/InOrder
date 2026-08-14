"""Small abstractions shared by compiled LangGraph workflows."""

from typing import Any, Dict, Generic, TypeVar

StateT = TypeVar("StateT")


class BaseNode(Generic[StateT]):
    name = "node"

    def __call__(self, state: StateT) -> Dict[str, Any]:
        return self.run(state)

    def run(self, state: StateT) -> Dict[str, Any]:
        raise NotImplementedError


class BaseGraph(Generic[StateT]):
    def build(self):
        raise NotImplementedError

    def compile(self):
        return self.build().compile()
