"""Context-aware, incremental order request rewriting."""

import json
from typing import Any, Mapping, Optional

from ..context.models import HistoryConversation, OrderContext
from ..infrastructure.llm import ChatMessage, LLMClient
from ..infrastructure.llm.text import strip_json_prefix
from ..infrastructure.llm.structured import call_with_format_repair
from ..intent.resolver import StructuredIntentError
from .models import RewriteResult


REWRITE_SYSTEM_PROMPT = """你是物流订单语义重写器。

你的任务是根据用户本轮输入、当前订单上下文和最近对话历史，将本轮订单请求改写成明确、可供实体提取器处理的增量语义。

输入优先级：
1. 用户本轮明确表达的内容；
2. 当前订单上下文，它代表当前订单事实；
3. 对话历史，只用于解决指代、省略和明确的历史引用。

规则：
- 只重写本轮请求，不执行订单操作，不查询历史订单，不修改订单上下文。
- 保留本轮动作语义，并与实体提取器的 action 枚举一致：加/再加/增加/补充表示 add（新增），设置/我要表示 set（设置），删除/不要/去掉表示 remove（移除），改成/换成/替换表示 replace（替换）。
- 用户表达增量操作时，extraction_text 只描述本轮新增或变更，不重复输出无关的已有字段。
- 不要虚构用户没有表达的货物、地址、时间、联系人或车型。
- 不要把历史订单自动合并到当前订单，除非用户明确引用历史信息。
- 只能使用上下文中明确存在的信息解决省略或指代；存在多个候选时选择基于当前订单上下文和最近对话最合理的解释，继续生成可执行文本，不得阻断提取链路。
- 当前上下文为空时，“再加一吨苹果”应保守重写为“本轮新增一吨苹果”，不因为“再加”强制澄清。

输出只能是 JSON 对象，不要输出 Markdown、解释或其他文字：
{
  "rewritten_text": "完整但只描述本轮语义的重写文本",
  "extraction_text": "供实体提取器使用的本轮增量文本",
  "rewritten_text": "...",
  "extraction_text": "..."
}

成功时 rewritten_text 和 extraction_text 必须是字符串，且 extraction_text 必须可供实体提取器处理。
"""


def _format_context(context: OrderContext) -> str:
    data = context.to_dict()
    lines = ["【当前订单上下文】"]
    for key, value in data.items():
        if value not in (None, "", [], {}):
            lines.append(f"{key}: {json.dumps(value, ensure_ascii=False) if isinstance(value, (dict, list)) else value}")
    return "\n".join(lines)


def _format_history(history: HistoryConversation, limit: Optional[int]) -> str:
    messages = history.as_llm_messages(limit)
    if not messages:
        return "【最近对话历史】\n（无）"
    lines = ["【最近对话历史】"]
    lines.extend(f"{message['role']}: {message['content']}" for message in messages)
    return "\n".join(lines)


def _build_user_message(message: str, history: HistoryConversation, order_context: OrderContext, history_limit: Optional[int]) -> str:
    return "\n\n".join([_format_context(order_context), _format_history(history, history_limit), "【用户本轮输入】\n" + message])


def parse_rewrite(value: Mapping[str, Any]) -> RewriteResult:
    required = ("rewritten_text", "extraction_text")
    for field_name in required:
        if field_name not in value:
            raise StructuredIntentError("rewrite output missing field: " + field_name)
    extra = set(value).difference(required)
    if extra:
        raise StructuredIntentError("rewrite output has unexpected field: " + sorted(extra)[0])
    if not isinstance(value["rewritten_text"], str) or not isinstance(value["extraction_text"], str):
        raise StructuredIntentError("rewrite text fields must be strings")
    return RewriteResult(value["rewritten_text"], value["extraction_text"])


def parse_rewrite_from_text(text: str) -> RewriteResult:
    try:
        value = json.loads(strip_json_prefix(text))
    except (TypeError, ValueError) as exc:
        raise StructuredIntentError("LLM returned invalid rewrite JSON") from exc
    if not isinstance(value, dict):
        raise StructuredIntentError("LLM rewrite output must be a JSON object")
    return parse_rewrite(value)


class OrderRewriteModel:
    def __init__(self, client: LLMClient):
        self.client = client

    def rewrite(self, message: str, history: HistoryConversation, order_context: OrderContext, history_limit: Optional[int] = 12) -> RewriteResult:
        if not message:
            raise ValueError("rewrite message must not be empty")
        user_message = _build_user_message(message, history, order_context, history_limit)
        messages = [ChatMessage("system", REWRITE_SYSTEM_PROMPT), ChatMessage("user", user_message)]
        return call_with_format_repair(self.client, messages, parse_rewrite_from_text, "上一次输出无法解析。请严格只返回 rewritten_text 和 extraction_text 两个字符串字段组成的 JSON 对象。")


def rewrite_order_request(client: LLMClient, message: str, history: HistoryConversation, order_context: OrderContext, history_limit: Optional[int] = 12) -> RewriteResult:
    return OrderRewriteModel(client).rewrite(message, history, order_context, history_limit)


__all__ = ["REWRITE_SYSTEM_PROMPT", "OrderRewriteModel", "rewrite_order_request", "parse_rewrite", "parse_rewrite_from_text"]
