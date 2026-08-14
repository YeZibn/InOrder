from typing import Any, Protocol, Sequence

from .config import LLMConfig
from .models import ChatMessage


class ChatTransport(Protocol):
    def complete(self, messages: Sequence[ChatMessage], config: LLMConfig) -> Any:
        ...


class OpenAITransport:
    """Thin adapter around the optional OpenAI-compatible SDK."""

    def __init__(self, config: LLMConfig):
        try:
            from openai import OpenAI
        except ImportError as exc:
            raise RuntimeError("The openai package is required for real LLM calls") from exc
        self._client = OpenAI(api_key=config.api_key, base_url=config.base_url, timeout=config.timeout)

    def complete(self, messages, config):
        request = {
            "model": config.model,
            "messages": [{"role": message.role, "content": message.content} for message in messages],
        }
        if config.reasoning_effort is not None:
            request["reasoning_effort"] = config.reasoning_effort
        return self._client.chat.completions.create(**request)
