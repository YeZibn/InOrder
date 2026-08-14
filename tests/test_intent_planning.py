import pytest

from inorder_llm.intent import (
    IntentPlan,
    IntentPlanValidationError,
    IntentPlanningSubgraph,
    IntentStep,
    validate_plan,
)


class FakeIntentModel:
    def __init__(self, main, candidates=()):
        self.main, self.candidates = main, list(candidates)
        self.calls = []

    def classify_main_intent(self, message):
        self.calls.append(("main", message))
        return {"main_intent": self.main, "confidence": 0.95}

    def extract_sub_intents(self, message, main_intent):
        self.calls.append(("sub", message, main_intent))
        return self.candidates


def test_single_order_intent():
    graph = IntentPlanningSubgraph(FakeIntentModel("order", [{"name": "create_order", "arguments": {"cargo": "货物"}}]))
    plan = graph.invoke("我要创建一个拉货订单")
    assert plan.main_intent == "order"
    assert plan.sub_intents[0].name == "create_order"
    assert plan.sub_intents[0].id == "step_1"
    assert not plan.needs_clarification


def test_history_then_modify_is_sequential_and_dependent():
    candidates = [
        {"id": "history", "name": "query_history_order", "arguments": {"reference": "最近一次"}},
        {"id": "draft", "name": "modify_draft", "arguments": {"target": "current_draft"}, "depends_on": ["history"]},
    ]
    plan = IntentPlanningSubgraph(FakeIntentModel("order", candidates)).invoke("参考历史订单修改当前草稿")
    assert [step.name for step in plan.sub_intents] == ["query_history_order", "modify_draft"]
    assert plan.sub_intents[1].depends_on == ("history",)


def test_qa_has_no_order_sub_intents():
    plan = IntentPlanningSubgraph(FakeIntentModel("qa")).invoke("什么是预约配送")
    assert plan.main_intent == "qa"
    assert plan.sub_intents == ()
    assert not plan.needs_clarification


def test_ambiguous_requires_clarification():
    plan = IntentPlanningSubgraph(FakeIntentModel("ambiguous")).invoke("帮我查一下并告诉我怎么下单")
    assert plan.needs_clarification
    assert plan.clarification_reason


def test_order_without_sub_intent_requires_clarification():
    plan = IntentPlanningSubgraph(FakeIntentModel("order")).invoke("帮我处理一下")
    assert plan.needs_clarification
    assert "订单操作" in plan.clarification_reason


def test_invalid_dependency_and_cycle_are_rejected():
    with pytest.raises(IntentPlanValidationError):
        validate_plan(IntentPlan("order", (IntentStep("a", "create_order", depends_on=("missing",)),)))
    with pytest.raises(IntentPlanValidationError):
        validate_plan(IntentPlan("order", (IntentStep("a", "create_order", depends_on=("b",)), IntentStep("b", "modify_draft", depends_on=("a",)))))


def test_recognition_only_does_not_execute_business_tools():
    model = FakeIntentModel("order", [{"name": "query_history_order"}, {"name": "modify_draft"}])
    plan = IntentPlanningSubgraph(model).invoke("查询历史订单并修改草稿")
    assert plan is not None
    assert model.calls == [("main", "查询历史订单并修改草稿"), ("sub", "查询历史订单并修改草稿", "order")]
