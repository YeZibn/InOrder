from typing import Any, Protocol, Sequence

from .config import LLMConfig
from .models import ChatMessage


class ResponsesTransport(Protocol):
    def complete(self, messages: Sequence[ChatMessage], config: LLMConfig) -> Any:
        ...


class OpenAITransport:
    """Configurable OpenAI-compatible transport."""

    def __init__(self, config: LLMConfig):
        try:
            from openai import OpenAI
        except ImportError as exc:
            raise RuntimeError("The openai package is required for real LLM calls") from exc
        self._client = OpenAI(api_key=config.api_key, base_url=config.base_url, timeout=config.timeout)

    def complete(self, messages, config):
        if config.api_mode == "chat_completions":
            request = {"model": config.model, "messages": [{"role": m.role, "content": m.content} for m in messages]}
            if config.reasoning_effort is not None:
                request["reasoning_effort"] = config.reasoning_effort
            return self._client.chat.completions.create(**request)
        request = {"model": config.model, "input": [{"role": m.role, "content": m.content} for m in messages]}
        if config.reasoning_effort is not None:
            request["reasoning"] = {"effort": config.reasoning_effort}
        return self._client.responses.create(**request)
