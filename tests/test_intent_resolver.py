import json

import pytest

from inorder_llm.intent import IntentPlan, IntentPlanValidationError, validate_plan
from inorder_llm.intent.resolver import (
    LLMIntentModel,
    MAIN_INTENT_SYSTEM_PROMPT,
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


class SequenceLLMClient:
    def __init__(self, texts):
        self.texts = list(texts)
        self.calls = []

    def chat(self, messages):
        self.calls.append(list(messages))
        return _Resp(self.texts.pop(0))


def test_main_intent_prompt_defines_order_and_qa_with_execution_priority():
    prompt = MAIN_INTENT_SYSTEM_PROMPT
    assert '"main_intent": "order" | "qa"' in prompt
    assert "期望的输出" in prompt
    assert "执行优先" in prompt
    assert "操作方法" in prompt
    assert "运货" in prompt
    assert "多少钱" in prompt
    assert "confidence" in prompt
    assert "不要提取子意图" in prompt



def test_classify_main_intent_sends_system_then_user_message():
    client = FakeLLMClient(json.dumps({"main_intent": "qa", "confidence": 0.8}))
    model = LLMIntentModel(client)
    result = model.classify_main_intent("什么是预约配送")
    messages = client.calls[0]
    assert [m.role for m in messages] == ["system", "user"]
    assert messages[0].content == MAIN_INTENT_SYSTEM_PROMPT
    assert messages[1].content == "什么是预约配送"
    assert result["main_intent"] == "qa"


def test_main_intent_accepts_invisible_stream_prefix():
    client = FakeLLMClient('\u200b{"main_intent":"qa","confidence":0.8}')
    assert LLMIntentModel(client).classify_main_intent("你好")["main_intent"] == "qa"



def test_invalid_json_raises_structured_error():
    client = FakeLLMClient("not json")
    model = LLMIntentModel(client)
    with pytest.raises(StructuredIntentError):
        model.classify_main_intent("hi")


def test_invalid_json_gets_one_format_repair_attempt():
    client = SequenceLLMClient(["not json", json.dumps({"main_intent": "qa", "confidence": 0.8})])
    assert LLMIntentModel(client).classify_main_intent("hi")["main_intent"] == "qa"
    assert len(client.calls) == 2


def test_invalid_json_repair_is_capped_at_one_attempt():
    client = SequenceLLMClient(["not json", "still not json", json.dumps({"main_intent": "qa"})])
    with pytest.raises(StructuredIntentError):
        LLMIntentModel(client).classify_main_intent("hi")
    assert len(client.calls) == 2


def test_non_dict_output_raises_structured_error():
    client = FakeLLMClient(json.dumps(["order"]))
    model = LLMIntentModel(client)
    with pytest.raises(StructuredIntentError):
        model.classify_main_intent("hi")


def test_confidence_must_be_between_zero_and_one():
    with pytest.raises(StructuredIntentError):
        LLMIntentModel(FakeLLMClient(json.dumps({"main_intent": "qa", "confidence": 2}))).classify_main_intent("hi")
