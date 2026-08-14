import time
from typing import Any, Sequence

from .config import LLMConfig
from .errors import AuthenticationError, InvalidRequestError, RateLimitError, TimeoutError, UpstreamError
from .models import ChatMessage, LLMResponse, Usage
from .transport import ChatTransport, OpenAITransport


class LLMClient:
    def __init__(self, config: LLMConfig, transport: ChatTransport = None, sleep=time.sleep):
        self.config = config
        self.transport = transport or OpenAITransport(config)
        self._sleep = sleep

    def chat(self, messages: Sequence[ChatMessage]) -> LLMResponse:
        if not messages:
            raise InvalidRequestError("messages must not be empty")
        for message in messages:
            if not message.role or not message.content:
                raise InvalidRequestError("each message requires a role and content")
        for attempt in range(self.config.max_retries + 1):
            try:
                return self._normalize(self.transport.complete(messages, self.config))
            except Exception as exc:
                error = self._normalize_error(exc)
                retryable = isinstance(error, (TimeoutError, UpstreamError, RateLimitError))
                if not retryable or attempt >= self.config.max_retries:
                    raise error from exc
                delay = error.retry_after if isinstance(error, RateLimitError) and error.retry_after is not None else self.config.backoff_seconds * (2 ** attempt)
                self._sleep(delay)
        raise AssertionError("unreachable")

    def _normalize(self, raw: Any) -> LLMResponse:
        message = raw.choices[0].message
        usage_raw = getattr(raw, "usage", None)
        usage = None if usage_raw is None else Usage(getattr(usage_raw, "prompt_tokens", None), getattr(usage_raw, "completion_tokens", None), getattr(usage_raw, "total_tokens", None))
        return LLMResponse(getattr(message, "content", "") or "", getattr(raw, "model", self.config.model), usage, {"id": getattr(raw, "id", None)})

    @staticmethod
    def _normalize_error(exc: Exception):
        name, text = exc.__class__.__name__.lower(), str(exc)
        if "authentication" in name or "permission" in name or "401" in text:
            return AuthenticationError("LLM authentication failed")
        if "ratelimit" in name or "rate limit" in text.lower() or "429" in text:
            return RateLimitError("LLM rate limit exceeded", getattr(exc, "retry_after", None))
        if "timeout" in name or "timed out" in text.lower():
            return TimeoutError("LLM request timed out")
        if "invalid" in name or "badrequest" in name or "400" in text:
            return InvalidRequestError("LLM request was rejected")
        return UpstreamError("LLM upstream request failed")
