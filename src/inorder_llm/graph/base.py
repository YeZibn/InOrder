"""Small abstractions shared by compiled LangGraph workflows."""

from dataclasses import dataclass
import time
from typing import Any, Callable, Dict, Generic, Mapping, TypeVar

from ..infrastructure.llm.errors import WorkflowTimeoutError

StateT = TypeVar("StateT")


class BaseNode(Generic[StateT]):
    name = "node"
    retry_policy = None

    def __call__(self, state: StateT) -> Dict[str, Any]:
        deadline = state.get("deadline_at") if isinstance(state, Mapping) else None
        if deadline is not None and time.monotonic() >= deadline:
            raise WorkflowTimeoutError(f"workflow deadline exceeded before {self.name}")
        return self.run(state)

    def run(self, state: StateT) -> Dict[str, Any]:
        raise NotImplementedError


class BaseGraph(Generic[StateT]):
    def build(self):
        raise NotImplementedError

    def compile(self):
        return self.build().compile()


@dataclass(frozen=True)
class NodeRetryPolicy:
    """Explicit opt-in node retry policy; nodes are not retried by default."""

    max_attempts: int = 1
    retry_if: Callable[[BaseException], bool] = lambda exc: False

    def run(self, operation: Callable[[], Dict[str, Any]]) -> Dict[str, Any]:
        attempts = 0
        while True:
            try:
                return operation()
            except BaseException as exc:
                attempts += 1
                if attempts >= self.max_attempts or not self.retry_if(exc):
                    raise


__all__ = ["BaseNode", "BaseGraph", "NodeRetryPolicy"]
