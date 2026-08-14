"""Recognition-only intent planning for future LangGraph workflows."""

from dataclasses import dataclass, field
import json
from typing import Any, Dict, List, Mapping, Optional, Protocol, Sequence

from .client import LLMClient
from .models import ChatMessage

MAIN_INTENTS = frozenset(("order", "qa", "ambiguous"))
ORDER_SUB_INTENTS = frozenset(("create_order", "modify_draft", "query_history_order"))


class IntentPlanningError(Exception):
    """Base error for intent recognition and plan validation."""


class StructuredIntentError(IntentPlanningError):
    pass


class IntentPlanValidationError(IntentPlanningError):
    pass


@dataclass(frozen=True)
class IntentStep:
    id: str
    name: str
    arguments: Mapping[str, Any] = field(default_factory=dict)
    depends_on: Sequence[str] = field(default_factory=tuple)

    def to_dict(self) -> Dict[str, Any]:
        result = {"id": self.id, "name": self.name, "arguments": dict(self.arguments)}
        if self.depends_on:
            result["depends_on"] = list(self.depends_on)
        return result


@dataclass(frozen=True)
class IntentPlan:
    main_intent: str
    sub_intents: Sequence[IntentStep] = field(default_factory=tuple)
    needs_clarification: bool = False
    clarification_reason: Optional[str] = None
    confidence: Optional[float] = None
    raw_message: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "main_intent": self.main_intent,
            "sub_intents": [step.to_dict() for step in self.sub_intents],
            "needs_clarification": self.needs_clarification,
            "clarification_reason": self.clarification_reason,
            "confidence": self.confidence,
            "raw_message": self.raw_message,
        }


@dataclass
class IntentPlanningState:
    message: str
    main_intent: Optional[str] = None
    candidates: List[Dict[str, Any]] = field(default_factory=list)
    sub_intents: List[IntentStep] = field(default_factory=list)
    plan: Optional[IntentPlan] = None
    needs_clarification: bool = False
    clarification_reason: Optional[str] = None
    confidence: Optional[float] = None


class IntentModel(Protocol):
    def classify_main_intent(self, message: str) -> Mapping[str, Any]:
        ...

    def extract_sub_intents(self, message: str, main_intent: str) -> Sequence[Mapping[str, Any]]:
        ...


class LLMIntentModel:
    """Structured-output adapter using the existing injectable LLMClient."""

    def __init__(self, client: LLMClient):
        self.client = client

    def _json_call(self, instruction: str) -> Mapping[str, Any]:
        response = self.client.chat([ChatMessage("system", instruction)])
        try:
            value = json.loads(response.text)
        except (TypeError, ValueError) as exc:
            raise StructuredIntentError("LLM returned invalid intent JSON") from exc
        if not isinstance(value, dict):
            raise StructuredIntentError("LLM intent output must be a JSON object")
        return value

    def classify_main_intent(self, message: str) -> Mapping[str, Any]:
        return self._json_call(
            "Classify the user's message. Return JSON only with keys "
            "main_intent (order, qa, ambiguous) and confidence. Message: " + message
        )

    def extract_sub_intents(self, message: str, main_intent: str) -> Sequence[Mapping[str, Any]]:
        value = self._json_call(
            "Extract zero or more order sub-intents. Return JSON only with key "
            "sub_intents, an array of objects with name, arguments, and optional depends_on. "
            "Allowed names: create_order, modify_draft, query_history_order. "
            "Message: " + message
        )
        items = value.get("sub_intents", [])
        if not isinstance(items, list):
            raise StructuredIntentError("sub_intents must be an array")
        return items


def _step_from_candidate(candidate: Mapping[str, Any], index: int) -> IntentStep:
    name = candidate.get("name")
    if not isinstance(name, str):
        raise IntentPlanValidationError("each sub-intent requires a name")
    depends_on = candidate.get("depends_on", ())
    if isinstance(depends_on, str):
        depends_on = (depends_on,)
    if not isinstance(depends_on, (list, tuple)):
        raise IntentPlanValidationError("depends_on must be an array")
    arguments = candidate.get("arguments", {})
    if not isinstance(arguments, dict):
        raise IntentPlanValidationError("arguments must be an object")
    return IntentStep(candidate.get("id", "step_" + str(index)), name, arguments, tuple(depends_on))


def validate_plan(plan: IntentPlan) -> IntentPlan:
    if plan.main_intent not in MAIN_INTENTS:
        raise IntentPlanValidationError("invalid main_intent: " + str(plan.main_intent))
    if plan.main_intent != "order" and plan.sub_intents:
        raise IntentPlanValidationError("only order intent may contain order sub-intents")
    ids = [step.id for step in plan.sub_intents]
    if len(ids) != len(set(ids)):
        raise IntentPlanValidationError("intent step ids must be unique")
    names = [step.name for step in plan.sub_intents]
    if any(name not in ORDER_SUB_INTENTS for name in names):
        raise IntentPlanValidationError("invalid order sub-intent")
    known = set(ids)
    for step in plan.sub_intents:
        if step.id in step.depends_on or any(dep not in known for dep in step.depends_on):
            raise IntentPlanValidationError("intent dependencies must reference other steps")
    visiting, visited = set(), set()

    def visit(step_id):
        if step_id in visiting:
            raise IntentPlanValidationError("intent dependencies must be acyclic")
        if step_id in visited:
            return
        visiting.add(step_id)
        step = next(step for step in plan.sub_intents if step.id == step_id)
        for dependency in step.depends_on:
            visit(dependency)
        visiting.remove(step_id)
        visited.add(step_id)

    for step_id in ids:
        visit(step_id)
    if plan.needs_clarification and not plan.clarification_reason:
        raise IntentPlanValidationError("clarification_reason is required when clarification is needed")
    return plan


class IntentPlanningSubgraph:
    """Small LangGraph-compatible subgraph facade with deterministic node boundaries."""

    def __init__(self, model: IntentModel):
        self.model = model

    def classify_main_intent(self, state: IntentPlanningState) -> IntentPlanningState:
        result = self.model.classify_main_intent(state.message)
        state.main_intent = result.get("main_intent")
        state.confidence = result.get("confidence")
        if state.main_intent not in MAIN_INTENTS:
            raise IntentPlanValidationError("invalid main_intent")
        if state.main_intent == "ambiguous":
            state.needs_clarification = True
            state.clarification_reason = "无法确定用户是要执行订单操作还是进行问答"
        return state

    def extract_sub_intents(self, state: IntentPlanningState) -> IntentPlanningState:
        if state.main_intent == "order":
            state.candidates = [dict(item) for item in self.model.extract_sub_intents(state.message, state.main_intent)]
        return state

    def normalize_sub_intents(self, state: IntentPlanningState) -> IntentPlanningState:
        state.sub_intents = [_step_from_candidate(item, index + 1) for index, item in enumerate(state.candidates)]
        return state

    def build_intent_plan(self, state: IntentPlanningState) -> IntentPlanningState:
        if state.main_intent == "order" and not state.sub_intents:
            state.needs_clarification = True
            state.clarification_reason = state.clarification_reason or "未识别出具体订单操作"
        state.plan = IntentPlan(state.main_intent, tuple(state.sub_intents), state.needs_clarification,
                                state.clarification_reason, state.confidence, state.message)
        return state

    def validate_intent_plan(self, state: IntentPlanningState) -> IntentPlanningState:
        state.plan = validate_plan(state.plan)
        return state

    def invoke(self, message: str) -> IntentPlan:
        state = IntentPlanningState(message=message)
        for node in (self.classify_main_intent, self.extract_sub_intents, self.normalize_sub_intents,
                     self.build_intent_plan, self.validate_intent_plan):
            state = node(state)
        return state.plan


def build_intent_planning_subgraph(model: IntentModel) -> IntentPlanningSubgraph:
    """Return a compiled-like facade; a LangGraph StateGraph can wrap these node methods later."""
    return IntentPlanningSubgraph(model)
