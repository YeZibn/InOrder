"""Compiled LangGraph skeleton for recognition-only intent routing."""

from typing import Any, Dict, List, Literal, Optional, TypedDict

from langgraph.graph import END, START, StateGraph

from .intent_planning import (
    IntentPlan,
    IntentStep,
    IntentModel,
    IntentPlanValidationError,
    _step_from_candidate,
    validate_plan,
)


class IntentGraphState(TypedDict, total=False):
    message: str
    main_intent: Literal["order", "qa", "ambiguous"]
    main_confidence: Optional[float]
    sub_intents: List[IntentStep]
    intent_plan: IntentPlan
    needs_clarification: bool
    clarification_reason: Optional[str]


def main_intent_node(model: IntentModel):
    def node(state: IntentGraphState) -> Dict[str, Any]:
        result = model.classify_main_intent(state["message"])
        main_intent = result.get("main_intent")
        if main_intent not in ("order", "qa", "ambiguous"):
            raise IntentPlanValidationError("invalid main_intent")
        update: Dict[str, Any] = {
            "main_intent": main_intent,
            "main_confidence": result.get("confidence"),
        }
        if main_intent == "ambiguous":
            update.update({
                "needs_clarification": True,
                "clarification_reason": "无法确定用户是要执行订单操作还是进行问答",
            })
        return update
    return node


def sub_intent_node(model: IntentModel):
    def node(state: IntentGraphState) -> Dict[str, Any]:
        if state.get("main_intent") != "order":
            raise IntentPlanValidationError("sub_intent_node requires order main_intent")
        candidates = model.extract_sub_intents(state["message"], "order")
        steps = [_step_from_candidate(dict(item), index + 1) for index, item in enumerate(candidates)]
        return {"sub_intents": steps}
    return node


def build_plan_node(state: IntentGraphState) -> Dict[str, Any]:
    main_intent = state["main_intent"]
    sub_intents = tuple(state.get("sub_intents", ()))
    needs_clarification = state.get("needs_clarification", False)
    reason = state.get("clarification_reason")
    if main_intent == "order" and not sub_intents:
        needs_clarification = True
        reason = reason or "未识别出具体订单操作"
    return {
        "intent_plan": IntentPlan(
            main_intent=main_intent,
            sub_intents=sub_intents,
            needs_clarification=needs_clarification,
            clarification_reason=reason,
            confidence=state.get("main_confidence"),
            raw_message=state.get("message"),
        ),
        "needs_clarification": needs_clarification,
        "clarification_reason": reason,
    }


def validate_plan_node(state: IntentGraphState) -> Dict[str, Any]:
    plan = validate_plan(state["intent_plan"])
    return {"intent_plan": plan}


def clarification_node(state: IntentGraphState) -> Dict[str, Any]:
    return {
        "needs_clarification": True,
        "clarification_reason": state.get("clarification_reason") or "需要进一步澄清用户意图",
    }


def finalize_node(state: IntentGraphState) -> Dict[str, Any]:
    if "intent_plan" not in state:
        return build_plan_node(state)
    return {"intent_plan": state["intent_plan"]}


def route_main_intent(state: IntentGraphState) -> Literal["order", "qa", "ambiguous"]:
    return state["main_intent"]


def build_intent_graph(model: IntentModel):
    """Build and compile the recognition-only intent StateGraph."""
    builder = StateGraph(IntentGraphState)
    builder.add_node("main_intent", main_intent_node(model))
    builder.add_node("sub_intent", sub_intent_node(model))
    builder.add_node("build_plan", build_plan_node)
    builder.add_node("validate_plan", validate_plan_node)
    builder.add_node("clarification", clarification_node)
    builder.add_node("finalize", finalize_node)
    builder.add_edge(START, "main_intent")
    builder.add_conditional_edges(
        "main_intent",
        route_main_intent,
        {"order": "sub_intent", "qa": "build_plan", "ambiguous": "clarification"},
    )
    builder.add_edge("sub_intent", "build_plan")
    builder.add_edge("build_plan", "validate_plan")
    builder.add_edge("validate_plan", "finalize")
    builder.add_edge("clarification", "finalize")
    builder.add_edge("finalize", END)
    return builder.compile()
