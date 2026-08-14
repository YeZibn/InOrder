import json

import pytest

from inorder_llm.intent import IntentPlan, IntentStep, IntentPlanValidationError, validate_plan
from inorder_llm.intent.resolver import (
    LLMIntentModel,
    MAIN_INTENT_SYSTEM_PROMPT,
    SUB_INTENT_SYSTEM_PROMPT,
    StructuredIntentError,
)


class _Resp:
    def __init__(self, text):
        self.text = text


class FakeLLMClient:
    def __init__(self, text):
        self.text = text
        self.calls = []

    def chat(self, messages):
        self.calls.append(list(messages))
        return _Resp(self.text)


def test_main_intent_prompt_defines_order_and_qa_with_execution_priority():
    prompt = MAIN_INTENT_SYSTEM_PROMPT
    assert '"main_intent": "order" | "qa"' in prompt
    assert "执行优先" in prompt
    assert "操作方法" in prompt
    assert "confidence" in prompt


def test_sub_intent_prompt_lists_allowed_names_and_depends_on_rules():
    prompt = SUB_INTENT_SYSTEM_PROMPT
    for name in ("create_order", "modify_draft", "query_history_order"):
        assert name in prompt
    assert "depends_on" in prompt
    assert "保守" in prompt
    assert "sub_intents" in prompt


def test_classify_main_intent_sends_system_then_user_message():
    client = FakeLLMClient(json.dumps({"main_intent": "qa", "confidence": 0.8}))
    model = LLMIntentModel(client)
    result = model.classify_main_intent("什么是预约配送")
    messages = client.calls[0]
    assert [m.role for m in messages] == ["system", "user"]
    assert messages[0].content == MAIN_INTENT_SYSTEM_PROMPT
    assert messages[1].content == "什么是预约配送"
    assert result["main_intent"] == "qa"


def test_extract_sub_intents_sends_system_then_user_message_and_parses_items():
    payload = {"sub_intents": [{"id": "step_1", "name": "create_order", "arguments": {"cargo": "钢材"}}]}
    client = FakeLLMClient(json.dumps(payload))
    model = LLMIntentModel(client)
    items = model.extract_sub_intents("创建拉货订单", "order")
    messages = client.calls[0]
    assert [m.role for m in messages] == ["system", "user"]
    assert messages[0].content == SUB_INTENT_SYSTEM_PROMPT
    assert messages[1].content == "创建拉货订单"
    assert items == payload["sub_intents"]


def test_invalid_json_raises_structured_error():
    client = FakeLLMClient("not json")
    model = LLMIntentModel(client)
    with pytest.raises(StructuredIntentError):
        model.classify_main_intent("hi")


def test_non_dict_output_raises_structured_error():
    client = FakeLLMClient(json.dumps(["order"]))
    model = LLMIntentModel(client)
    with pytest.raises(StructuredIntentError):
        model.classify_main_intent("hi")


def test_sub_intents_not_array_raises_structured_error():
    client = FakeLLMClient(json.dumps({"sub_intents": {"name": "create_order"}}))
    model = LLMIntentModel(client)
    with pytest.raises(StructuredIntentError):
        model.extract_sub_intents("hi", "order")


def test_invalid_dependency_and_cycle_are_rejected():
    with pytest.raises(IntentPlanValidationError):
        validate_plan(IntentPlan("order", (IntentStep("a", "create_order", depends_on=("missing",)),)))
    with pytest.raises(IntentPlanValidationError):
        validate_plan(IntentPlan("order", (
            IntentStep("a", "create_order", depends_on=("b",)),
            IntentStep("b", "modify_draft", depends_on=("a",)),
        )))
