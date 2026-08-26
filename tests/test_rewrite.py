import json

import pytest

from inorder_llm.context import HistoryConversation, OrderContext
from inorder_llm.infrastructure.llm import LLMResponse
from inorder_llm.intent.resolver import StructuredIntentError
from inorder_llm.rewrite import (REWRITE_SYSTEM_PROMPT, OrderRewriteModel,
                                 RewriteResult, parse_rewrite_from_text)


class FakeClient:
    def __init__(self, payload):
        self.payload = payload
        self.calls = []

    def chat(self, messages):
        self.calls.append(messages)
        return LLMResponse(json.dumps(self.payload, ensure_ascii=False), "test")


class SequenceClient:
    def __init__(self, payloads):
        self.payloads = list(payloads)
        self.calls = []

    def chat(self, messages):
        self.calls.append(messages)
        payload = self.payloads.pop(0)
        return LLMResponse(payload, "test")


def test_rewrite_includes_request_reference_time():
    client = FakeClient({"rewritten_text": "明天发货", "extraction_text": "明天发货"})
    OrderRewriteModel(client).rewrite(
        "明天发货", HistoryConversation(), OrderContext(), reference_time="2026-08-26 10:00"
    )
    assert "【参考时间】2026-08-26 10:00" in client.calls[0][1].content


def test_rewrite_format_repair_reuses_reference_time():
    client = SequenceClient([
        "not-json",
        json.dumps({"rewritten_text": "明天发货", "extraction_text": "明天发货"}, ensure_ascii=False),
    ])
    result = OrderRewriteModel(client).rewrite(
        "明天发货", HistoryConversation(), OrderContext(), reference_time="2026-08-26 10:00"
    )
    assert result.extraction_text == "明天发货"
    assert len(client.calls) == 2
    assert all("【参考时间】2026-08-26 10:00" in messages[1].content for messages in client.calls)


def test_rewrite_result_serializes():
    result = RewriteResult("已有苹果，本轮新增香蕉", "新增一吨香蕉")
    assert result.to_dict() == {"rewritten_text": "已有苹果，本轮新增香蕉", "extraction_text": "新增一吨香蕉"}


def test_rewrite_incremental_cargo_and_message_sections():
    client = FakeClient({"rewritten_text": "当前已有一吨香蕉，本轮新增一吨苹果", "extraction_text": "新增一吨苹果"})
    history = HistoryConversation()
    history.append_user("我要一吨香蕉")
    context = OrderContext(cargo=[{"name": "香蕉", "weight": "1吨"}])
    result = OrderRewriteModel(client).rewrite("再加一吨苹果", history, context)
    assert result.extraction_text == "新增一吨苹果"
    assert context.cargo == [{"name": "香蕉", "weight": "1吨"}]
    system, user = client.calls[0]
    assert system.role == "system" and user.role == "user"
    assert "【当前订单上下文】" in user.content
    assert "【最近对话历史】" in user.content
    assert "【用户本轮输入】" in user.content


def test_rewrite_prompt_contains_action_and_conservative_rules():
    assert "add" in REWRITE_SYSTEM_PROMPT
    assert "remove" in REWRITE_SYSTEM_PROMPT
    assert "replace" in REWRITE_SYSTEM_PROMPT
    assert "最合理的解释" in REWRITE_SYSTEM_PROMPT
    assert "extraction_text" in REWRITE_SYSTEM_PROMPT


@pytest.mark.parametrize("payload", [
    {},
    {"rewritten_text": "x"},
    {"rewritten_text": "x", "extraction_text": "x", "needs_clarification": False},
    {"rewritten_text": 1, "extraction_text": "x", "needs_clarification": False, "clarification_reason": None},
])
def test_invalid_rewrite_output(payload):
    with pytest.raises(StructuredIntentError):
        parse_rewrite_from_text(json.dumps(payload))


def test_best_effort_rewrite_has_no_clarification_fields():
    result = parse_rewrite_from_text(json.dumps({"rewritten_text": "选择当前订单中的车辆", "extraction_text": "设置当前车辆"}))
    assert result.to_dict() == {"rewritten_text": "选择当前订单中的车辆", "extraction_text": "设置当前车辆"}


def test_rewrite_accepts_invisible_stream_prefix():
    result = parse_rewrite_from_text("\ufeff\u200b{" + '"rewritten_text":"x","extraction_text":"x"}' )
    assert result.rewritten_text == "x"
