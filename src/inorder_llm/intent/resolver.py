import json
from typing import Any, Mapping

from ..infrastructure.llm import ChatMessage, LLMClient
from ..infrastructure.llm.text import strip_json_prefix
from ..infrastructure.llm.structured import call_with_format_repair
from .protocols import IntentModel


class IntentPlanningError(Exception):
    """Base error for intent recognition and plan validation."""


class StructuredIntentError(IntentPlanningError):
    pass


MAIN_INTENT_SYSTEM_PROMPT = """你是一个运输订单管理助手的主意图分类器。请将用户消息分类为唯一的主意图，不要提取子意图、订单字段或澄清信息。

判据：用户期望的输出类型，而非是否使用命令动词。
- order：用户期望的输出是行动/结果，即想让一次运输或订单发生。包括当前订单创建或修改和业务目标愿望陈述（运货/发货/配送/托运/下单等），不要求使用显式命令动词。
- qa：用户期望的输出是信息（物流、商品、规则、操作方法、一般知识），没有要求让运输/订单发生。

领域映射（InOrder 为运输订单助手，以下业务目标词均表示 order）：
- 运货、发货、配送、托运、下单 -> order

咨询信号只能结合完整语义判断：当用户只是询问能力、价格、规则或操作方法时归 qa；若“可以吗/能不能”等礼貌表达中仍明确要求系统代为执行订单，则归 order。

决策规则：
- 业务目标愿望陈述（如“我想从上海运货到温州”）归 order，即使没有命令动词。
- 若消息同时包含信息询问和明确的订单执行请求，归 order（执行优先）。
- 纯操作方法类问题（如“怎么下单”、“订单怎么取消”）归 qa，因为用户在寻求指导而非要求代为执行。
- 能力/条件咨询（如“上海到温州能运吗”）归 qa，即便隐含后续下单可能；深层需求推测不在分类层进行。

边界示例：
- “创建一单 2 吨钢材的运输订单” -> order
- “我想从上海运货到温州” -> order（业务目标愿望，无命令动词）
- “什么是预约配送？” -> qa
- “怎么下单？” -> qa
- “运货到温州多少钱” -> qa（咨询价格）
- “上海到温州能运吗” -> qa（咨询能力）
- “可以帮我运一吨苹果吗” -> order（礼貌表达中的明确执行请求）
- “查一下并告诉我怎么下单” -> qa（寻求指导，无执行请求）

输出：仅返回符合以下 schema 的 JSON 对象，不得包含任何其他键：
{"main_intent": "order" | "qa", "confidence": <0 到 1 之间的数值>}
不要包含任何其他键、文字或解释。
"""


class LLMIntentModel:
    def __init__(self, client: LLMClient):
        self.client = client

    def _json_call(self, system_prompt: str, user_message: str) -> Mapping[str, Any]:
        messages = [
            ChatMessage("system", system_prompt),
            ChatMessage("user", user_message),
        ]
        def parse(text):
            try:
                value = json.loads(strip_json_prefix(text))
            except (TypeError, ValueError) as exc:
                raise StructuredIntentError("LLM returned invalid intent JSON") from exc
            if not isinstance(value, dict):
                raise StructuredIntentError("LLM intent output must be a JSON object")
            return value
        return call_with_format_repair(self.client, messages, parse, "上一次输出无法解析。请严格只返回符合要求的 JSON 对象，不要添加解释或 Markdown。")

    def classify_main_intent(self, message: str) -> Mapping[str, Any]:
        value = dict(self._json_call(MAIN_INTENT_SYSTEM_PROMPT, message))
        if value.get("main_intent") not in ("order", "qa"):
            raise StructuredIntentError("main_intent must be order or qa")
        confidence = value.get("confidence")
        if isinstance(confidence, bool) or not isinstance(confidence, (int, float)) or not 0 <= confidence <= 1:
            raise StructuredIntentError("confidence must be a number between 0 and 1")
        return {"main_intent": value["main_intent"], "confidence": float(confidence)}


__all__ = ["LLMIntentModel", "StructuredIntentError", "MAIN_INTENT_SYSTEM_PROMPT"]
