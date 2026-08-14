import json
from typing import Any, Mapping, Sequence

from ..infrastructure.llm import ChatMessage, LLMClient
from .protocols import IntentModel


class IntentPlanningError(Exception):
    """Base error for intent recognition and plan validation."""


class StructuredIntentError(IntentPlanningError):
    pass


MAIN_INTENT_SYSTEM_PROMPT = """你是一个订单管理助手的意图分类器。请将用户消息分类为唯一的主意图。

定义：
- order：用户要求系统执行、创建、修改或查询订单相关操作，即存在执行请求。
- qa：用户只是询问信息（物流、商品、规则、操作方法、一般知识），没有要求系统代为执行订单操作。

决策规则（执行优先）：
- 若消息中包含任何明确的订单执行请求，则判定为 order，即使消息同时包含提问。
- 纯操作方法类问题（如“怎么下单”、“订单怎么取消”）应判定为 qa，因为用户是在寻求指导，而非要求系统代为执行。

边界示例：
- “创建一单 2 吨钢材的运输订单” -> order
- “用最近的历史订单修改当前草稿” -> order
- “查询我的历史订单” -> order
- “什么是预约配送？” -> qa
- “怎么下单？” -> qa
- “查一下并告诉我怎么下单” -> qa（寻求指导，无执行请求）

输出：仅返回符合以下 schema 的 JSON 对象：
{"main_intent": "order" | "qa", "confidence": <0 到 1 之间的数值>}
不要包含任何其他键、文字或解释。
"""


SUB_INTENT_SYSTEM_PROMPT = """你是一个订单管理助手的订单子意图提取器。主意图已确定为 "order"。请从用户消息中提取零个或多个订单子意图。

允许的子意图名称：
- create_order：创建新订单草稿
- modify_draft：修改当前订单草稿
- query_history_order：查询历史订单

规则：
- 识别用户明确要求的每一个独立订单动作，不要臆造用户未提及的动作。
- 保守提取参数：仅包含用户明确表述或直接暗示的字段，绝不捏造取值。
- 当某个子意图的执行依赖另一个子意图的结果时，用 depends_on 引用对方步骤的 id 来表达；不得臆造依赖，相互独立的子意图不应有 depends_on。
- 为每个步骤分配形如 "step_<n>" 的稳定 id。

输出：仅返回符合以下 schema 的 JSON 对象：
{"sub_intents": [{"id": "step_1", "name": "create_order" | "modify_draft" | "query_history_order", "arguments": {...}, "depends_on": ["step_<n>"]}]}
- "id" 必填；"arguments" 为空时默认为 {}；"depends_on" 可选，为空时省略。
- 未识别到订单子意图时返回 {"sub_intents": []}。
不要包含任何其他键、文字或解释。
"""


class LLMIntentModel:
    def __init__(self, client: LLMClient):
        self.client = client

    def _json_call(self, system_prompt: str, user_message: str) -> Mapping[str, Any]:
        response = self.client.chat([
            ChatMessage("system", system_prompt),
            ChatMessage("user", user_message),
        ])
        try:
            value = json.loads(response.text)
        except (TypeError, ValueError) as exc:
            raise StructuredIntentError("LLM returned invalid intent JSON") from exc
        if not isinstance(value, dict):
            raise StructuredIntentError("LLM intent output must be a JSON object")
        return value

    def classify_main_intent(self, message: str) -> Mapping[str, Any]:
        return self._json_call(MAIN_INTENT_SYSTEM_PROMPT, message)

    def extract_sub_intents(self, message: str, main_intent: str) -> Sequence[Mapping[str, Any]]:
        value = self._json_call(SUB_INTENT_SYSTEM_PROMPT, message)
        items = value.get("sub_intents", [])
        if not isinstance(items, list):
            raise StructuredIntentError("sub_intents must be an array")
        return items


__all__ = ["LLMIntentModel", "StructuredIntentError"]
