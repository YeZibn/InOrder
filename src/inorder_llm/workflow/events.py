"""Safe, transport-independent events emitted by the parent workflow."""

from dataclasses import dataclass
from enum import Enum
import json
from typing import Any, Mapping


class EventType(str, Enum):
    THINKING_START = "THINKING_START"
    THINKING_STEP = "THINKING_STEP"
    THINKING_DONE = "THINKING_DONE"
    CREATE_ORDER_CONTEXT = "CREATE_ORDER_CONTEXT"
    DONE = "DONE"
    ERROR = "ERROR"


def _json_value(value: Any) -> Any:
    if hasattr(value, "to_dict"):
        return _json_value(value.to_dict())
    if isinstance(value, Mapping):
        return {str(k): _json_value(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_value(v) for v in value]
    return value


@dataclass(frozen=True)
class WorkflowEvent:
    type: EventType
    payload: Mapping[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {"type": self.type.value, "payload": _json_value(dict(self.payload))}

    def frame(self) -> str:
        return "data: " + json.dumps(self.to_dict(), ensure_ascii=False, separators=(",", ":")) + "\n\n"


def sse_frame(event: WorkflowEvent) -> str:
    return event.frame()


def error_event(exc: BaseException, stage: str = "workflow") -> WorkflowEvent:
    # Never expose exception text: upstream messages can contain prompts, keys, or stack details.
    name = exc.__class__.__name__
    code = {
        "AuthenticationError": "LLM_AUTHENTICATION_ERROR",
        "RateLimitError": "LLM_RATE_LIMITED",
        "TimeoutError": "LLM_TIMEOUT",
        "ConfigurationError": "CONFIGURATION_ERROR",
        "InvalidRequestError": "INVALID_REQUEST",
        "WorkflowTimeoutError": "WORKFLOW_TIMEOUT",
        "UpstreamError": "LLM_UPSTREAM_ERROR",
    }.get(name, "WORKFLOW_ERROR")
    message = {
        "LLM_AUTHENTICATION_ERROR": "模型服务认证失败",
        "LLM_RATE_LIMITED": "模型服务请求过于频繁",
        "LLM_TIMEOUT": "模型服务请求超时",
        "CONFIGURATION_ERROR": "服务配置错误",
        "INVALID_REQUEST": "请求参数无效",
        "WORKFLOW_TIMEOUT": "工作流处理超时",
        "LLM_UPSTREAM_ERROR": "模型服务暂时不可用",
    }.get(code, "工作流处理失败")
    retryable = bool(getattr(exc, "retryable", False)) and code != "WORKFLOW_TIMEOUT"
    return WorkflowEvent(EventType.ERROR, {"code": code, "message": message, "stage": stage, "retryable": retryable})
