"""Observe a compiled MainGraph without duplicating child graph nodes."""

import asyncio
from collections.abc import Iterator, Mapping
from copy import deepcopy
from dataclasses import dataclass, field
import inspect
import time
from typing import Any

from .events import EventType, WorkflowEvent, error_event
from ..infrastructure.llm.errors import WorkflowTimeoutError


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

# Node-level titles are deliberately static and user-facing.  The node name is
# included as a stable machine field, but is never used as display text by the
# browser.
_NODE_TEXT = {
    "main_intent": ("intent", "主意图识别完成"),
    "finalize": ("order", "订单处理结果整理完成"),
    "rewrite": ("order", "订单语义整理完成"),
    "extract": ("order", "订单字段提取完成"),
    "update_context": ("order", "订单信息更新完成"),
    "cargo_profile": ("cargo_profile", "货物画像生成完成"),
    "vehicle_resolution": ("vehicle", "车型匹配完成"),
    "order_completeness": ("order", "订单信息检查完成"),
}

_PUBLIC_STAGES = {"intent", "order", "cargo_profile", "vehicle"}


@dataclass
class _Observed:
    result: dict[str, Any] | None = None
    emitted: set[str] = field(default_factory=set)
    emitted_nodes: set[tuple] = field(default_factory=set)
    nested_seen: bool = False
    sequence: int = 0


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
        observed = _Observed()
        try:
            stream = getattr(self.graph, "stream", None)
            if callable(stream):
                for update in stream(dict(state), **self._stream_kwargs(stream)):
                    self._check_deadline(state)
                    yield from self._consume_update(update, observed)
                if observed.result is None:
                    observed.result = dict(self.graph.invoke(dict(state)))
            else:
                self._check_deadline(state)
                observed.result = dict(self.graph.invoke(dict(state)))
            self._check_deadline(state)
        except Exception as exc:
            yield error_event(exc, self._error_stage(observed.emitted))
            return
        yield from self._finish(state, observed)

    async def aevents(self, state: Mapping[str, Any]):
        """Observe a compiled async graph without blocking the API event loop."""
        yield WorkflowEvent(EventType.THINKING_START, {"title": "开始处理", "stage": "start"})
        observed = _Observed()
        stream = getattr(self.graph, "astream", None)
        if not callable(stream):
            raise TypeError("API graph must support astream")
        iterator = stream(dict(state), **self._stream_kwargs(stream)).__aiter__()
        try:
            while True:
                self._check_deadline(state)
                deadline = state.get("deadline_at")
                remaining = deadline - time.monotonic() if deadline is not None else None
                try:
                    if remaining is None:
                        update = await iterator.__anext__()
                    else:
                        update = await asyncio.wait_for(iterator.__anext__(), timeout=max(0, remaining))
                except StopAsyncIteration:
                    break
                except asyncio.TimeoutError as exc:
                    raise WorkflowTimeoutError("workflow deadline exceeded") from exc
                for event in self._consume_update(update, observed):
                    yield event
            if observed.result is None:
                self._check_deadline(state)
                observed.result = dict(await self.graph.ainvoke(dict(state)))
            self._check_deadline(state)
        except Exception as exc:
            yield error_event(exc, self._error_stage(observed.emitted))
            return
        finally:
            close = getattr(iterator, "aclose", None)
            if callable(close):
                await close()
        for event in self._finish(state, observed):
            yield event

    @staticmethod
    def _stream_kwargs(stream):
        kwargs = {"stream_mode": "updates"}
        try:
            parameters = inspect.signature(stream).parameters
            if "subgraphs" in parameters or any(p.kind is inspect.Parameter.VAR_KEYWORD for p in parameters.values()):
                kwargs["subgraphs"] = True
            if "version" in parameters:
                kwargs["version"] = "v2"
        except (TypeError, ValueError):
            pass
        return kwargs

    def _consume_update(self, update, observed: _Observed) -> Iterator[WorkflowEvent]:
        namespace, data = self._stream_update(update)
        if not isinstance(data, Mapping):
            return
        is_nested = bool(namespace)
        observed.nested_seen = observed.nested_seen or is_nested
        for node, value in data.items():
            node = self._node_name(node)
            if is_nested:
                public = self._public_node(node)
                node_key = (namespace, node)
                if public and node_key not in observed.emitted_nodes:
                    observed.emitted_nodes.add(node_key)
                    observed.emitted.add(public[0])
                    observed.sequence += 1
                    yield self._step(public[0], public[1], observed.sequence, node=node)
            elif not observed.nested_seen:
                public = self._public_stage(node, value)
                if public and public[0] not in observed.emitted:
                    observed.emitted.add(public[0])
                    observed.sequence += 1
                    yield self._step(public[0], public[1], observed.sequence)
            if isinstance(value, Mapping):
                observed.result = {**(observed.result or {}), **value}
            elif not is_nested:
                observed.result = {**(observed.result or {}), node: value}
        if is_nested and not any(isinstance(value, Mapping) for value in data.values()):
            observed.result = {**(observed.result or {}), **data}

    def _finish(self, state: Mapping[str, Any], observed: _Observed) -> Iterator[WorkflowEvent]:
        result = observed.result or {}
        emitted = observed.emitted
        sequence = observed.sequence
        # Compatibility graphs may return a new context without carrying the
        # request-bound anchor initialized at the API boundary. Preserve it in
        # the public result without mutating the graph input.
        anchor = state.get("reference_time")
        if anchor and isinstance(result, Mapping):
            order_result = result.get("order_result")
            context = order_result.get("order_context") if isinstance(order_result, Mapping) else result.get("order_context")
            if context is not None and hasattr(context, "reference_time") and not context.reference_time:
                preserved = deepcopy(context)
                preserved.reference_time = anchor
                result = dict(result)
                if isinstance(order_result, Mapping):
                    updated_order = dict(order_result)
                    updated_order["order_context"] = preserved
                    result["order_result"] = updated_order
                else:
                    result["order_context"] = preserved

        # Compiled parent graphs normally expose child graphs as one update. Derive
        # their public boundaries from the final structured state, never from LLM text.
        if "intent" not in emitted and "intent_subgraph" not in emitted:
            sequence += 1
            yield self._step("intent", "识别用户意图", sequence)
            emitted.add("intent")
        if result.get("order_graph_entered"):
            order_result = result.get("order_result") or result
            if "order" not in emitted:
                emitted.add("order")
                sequence += 1
                yield self._step("order", "处理订单", sequence)
            if order_result.get("cargo_profile_updated") and "cargo_profile" not in emitted:
                emitted.add("cargo_profile")
                sequence += 1
                yield self._step("cargo_profile", "生成货物画像", sequence)
            if order_result.get("vehicle_resolution") and "vehicle" not in emitted:
                emitted.add("vehicle")
                sequence += 1
                yield self._step("vehicle", "处理车型", sequence)
        if result.get("order_graph_entered"):
            order_result = result.get("order_result") or result
            context = order_result.get("order_context")
            if context is not None and order_result.get("order_context_updated"):
                payload = {"order_context": context, "session_id": state.get("session_id")} 
                yield WorkflowEvent(EventType.CREATE_ORDER_CONTEXT, payload)
        yield WorkflowEvent(EventType.THINKING_DONE, {"stage": "complete", "title": "处理完成"})
        yield WorkflowEvent(EventType.DONE, {"result": self._safe_result(result), "session_id": state.get("session_id")})

    @staticmethod
    def _step(stage: str, title: str, sequence: int, node: str | None = None) -> WorkflowEvent:
        payload = {"stage": stage, "title": title, "sequence": sequence}
        if node is not None:
            payload.update({"node": node, "status": "completed"})
        return WorkflowEvent(EventType.THINKING_STEP, payload)

    @staticmethod
    def _stream_update(update: Any) -> tuple[tuple[str, ...], Any]:
        """Normalize LangGraph v1/v2 nested stream records."""
        # v2: {"type": "updates", "ns": (...), "data": {...}}
        if isinstance(update, Mapping) and "data" in update and "ns" in update:
            namespace = update.get("ns") or ()
            if isinstance(namespace, str):
                namespace = (namespace,)
            return tuple(str(item) for item in namespace), update.get("data")
        # v1 with subgraphs=True: (namespace, data)
        if isinstance(update, tuple) and len(update) == 2 and isinstance(update[0], (tuple, list)):
            return tuple(str(item) for item in update[0]), update[1]
        return (), update

    @staticmethod
    def _node_name(node: Any) -> str:
        value = str(node)
        # Namespaces carry an opaque run id after a colon; node keys normally do
        # not, but stripping it keeps compatibility with wrappers that flatten
        # the namespace into the key.
        return value.split(":", 1)[0]

    @staticmethod
    def _public_node(node: str):
        return _NODE_TEXT.get(node)

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
        allowed = ("intent_result", "order_result", "order_graph_entered", "order_summary", "qa_placeholder")
        return {key: result[key] for key in allowed if key in result}

    @staticmethod
    def _error_stage(emitted):
        return "intent" if not emitted else "workflow"

    @staticmethod
    def _check_deadline(state):
        deadline = state.get("deadline_at")
        if deadline is not None and time.monotonic() >= deadline:
            raise WorkflowTimeoutError("workflow deadline exceeded")
