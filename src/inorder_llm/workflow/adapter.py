"""Observe a compiled MainGraph without duplicating child graph nodes."""

from collections.abc import Iterator, Mapping
from typing import Any

from .events import EventType, WorkflowEvent, error_event


_STAGE_TEXT = {
    "intent_subgraph": "识别用户意图",
    "order_subgraph": "处理订单",
    # These are internal order-subgraph nodes. They intentionally share the
    # public order stage so clients do not depend on implementation details.
    "rewrite": "处理订单",
    "extract": "处理订单",
    "update_context": "处理订单",
    "cargo_profile": "生成货物画像",
    "vehicle_resolution": "处理车型",
}

_PUBLIC_STAGES = {"intent", "order", "cargo_profile", "vehicle"}


class WorkflowEventAdapter:
    """Turn one parent-graph execution into safe lifecycle events.

    The graph remains the source of business truth. When available, ``stream``
    is used only to observe node boundaries; graphs exposing only ``invoke``
    remain supported for tests and existing integrations.
    """

    def __init__(self, graph):
        self.graph = graph

    def events(self, state: Mapping[str, Any]) -> Iterator[WorkflowEvent]:
        yield WorkflowEvent(EventType.THINKING_START, {"title": "开始处理", "stage": "start"})
        result: dict[str, Any] | None = None
        emitted = set()
        try:
            stream = getattr(self.graph, "stream", None)
            if callable(stream):
                # Consume updates to retain synchronous final semantics while observing boundaries.
                for update in stream(dict(state), stream_mode="updates"):
                    if not isinstance(update, Mapping):
                        continue
                    for node, value in update.items():
                        node = str(node)
                        public = self._public_stage(node, value)
                        if public and public[0] not in emitted:
                            emitted.add(public[0])
                            yield self._step(public[0], public[1], len(emitted))
                        if isinstance(value, Mapping):
                            result = {**(result or {}), **value}
                if result is None:
                    result = dict(self.graph.invoke(dict(state)))
            else:
                result = dict(self.graph.invoke(dict(state)))
        except BaseException as exc:
            yield error_event(exc, self._error_stage(emitted))
            return

        # Compiled parent graphs normally expose child graphs as one update. Derive
        # their public boundaries from the final structured state, never from LLM text.
        if "intent" not in emitted and "intent_subgraph" not in emitted:
            yield self._step("intent", "识别用户意图", len(emitted) + 1)
            emitted.add("intent")
        if result.get("order_graph_entered"):
            order_result = result.get("order_result") or result
            if "order" not in emitted:
                emitted.add("order")
                yield self._step("order", "处理订单", len(emitted))
            if order_result.get("cargo_profile_updated") and "cargo_profile" not in emitted:
                emitted.add("cargo_profile")
                yield self._step("cargo_profile", "生成货物画像", len(emitted))
            if order_result.get("vehicle_resolution") and "vehicle" not in emitted:
                emitted.add("vehicle")
                yield self._step("vehicle", "处理车型", len(emitted))
        if result.get("order_graph_entered"):
            order_result = result.get("order_result") or result
            context = order_result.get("order_context")
            if context is not None and order_result.get("order_context_updated"):
                payload = {"order_context": context, "session_id": state.get("session_id")} 
                yield WorkflowEvent(EventType.CREATE_ORDER_CONTEXT, payload)
        yield WorkflowEvent(EventType.THINKING_DONE, {"stage": "complete", "title": "处理完成"})
        yield WorkflowEvent(EventType.DONE, {"result": self._safe_result(result), "session_id": state.get("session_id")})

    @staticmethod
    def _step(stage: str, title: str, sequence: int) -> WorkflowEvent:
        return WorkflowEvent(EventType.THINKING_STEP, {"stage": stage, "title": title, "sequence": sequence})

    @staticmethod
    def _public_stage(node: str, value: Any):
        if node in _STAGE_TEXT:
            if node == "intent_subgraph":
                return ("intent", _STAGE_TEXT[node])
            if node in ("order_subgraph", "rewrite", "extract", "update_context"):
                return ("order", "处理订单")
            if node == "cargo_profile":
                return ("cargo_profile", _STAGE_TEXT[node])
            if node == "vehicle_resolution":
                return ("vehicle", _STAGE_TEXT[node])
        return None

    @staticmethod
    def _safe_result(result: Mapping[str, Any]) -> dict[str, Any]:
        # Final event contains only already structured public summaries.
        allowed = ("intent_result", "order_result", "order_graph_entered", "qa_placeholder")
        return {key: result[key] for key in allowed if key in result}

    @staticmethod
    def _error_stage(emitted):
        return "intent" if not emitted else "workflow"
