import time
from typing import Any, Callable, Optional, Sequence

from .config import LLMConfig
from .errors import AuthenticationError, InvalidRequestError, RateLimitError, TimeoutError, UpstreamError
from .models import ChatMessage, LLMResponse, LLMStreamEvent, Usage
from .transport import OpenAITransport, ResponsesTransport


class LLMClient:
    def __init__(
        self,
        config: LLMConfig,
        transport: ResponsesTransport = None,
        sleep=time.sleep,
        on_content: Optional[Callable[[str], None]] = None,
    ):
        self.config = config
        self.transport = transport or OpenAITransport(config)
        self._sleep = sleep
        self._on_content = on_content

    def chat(self, messages: Sequence[ChatMessage]) -> LLMResponse:
        if self.config.streaming:
            return self.stream(messages)
        self._validate_messages(messages)
        for attempt in range(self.config.max_retries + 1):
            try:
                response = self._normalize(self.transport.complete(messages, self.config))
                if self._on_content is not None:
                    self._on_content(response.text)
                return response
            except Exception as exc:
                error = self._normalize_error(exc)
                retryable = isinstance(error, (TimeoutError, UpstreamError, RateLimitError))
                if not retryable or attempt >= self.config.max_retries:
                    raise error from exc
                delay = error.retry_after if isinstance(error, RateLimitError) and error.retry_after is not None else min(self.config.backoff_max_seconds, self.config.backoff_seconds * (2 ** attempt))
                self._sleep(delay)
        raise AssertionError("unreachable")

    def stream(self, messages: Sequence[ChatMessage], on_delta: Optional[Callable[[str], None]] = None) -> LLMResponse:
        self._validate_messages(messages)
        callback = on_delta or self._on_content
        for attempt in range(self.config.max_retries + 1):
            received = False
            chunks = []
            try:
                events = self.transport.stream(messages, self.config)
                final_event = None
                for raw_event in events:
                    event = self._stream_event(raw_event)
                    if event.event_type in ("response.failed", "failed", "error"):
                        raise UpstreamError("LLM streaming response failed")
                    final_event = event
                    if event.event_type == "content_delta" and event.delta:
                        received = True
                        chunks.append(event.delta)
                        if callback is not None:
                            callback(event.delta)
                text = "".join(chunks)
                metadata = dict(final_event.metadata or {}) if final_event else {}
                if final_event and final_event.model:
                    model = final_event.model
                else:
                    model = self.config.model
                return LLMResponse(text, model, final_event.usage if final_event else None, metadata)
            except Exception as exc:
                error = self._normalize_error(exc)
                retryable = isinstance(error, (TimeoutError, UpstreamError, RateLimitError))
                if received or not retryable or attempt >= self.config.max_retries:
                    raise error from exc
                delay = error.retry_after if isinstance(error, RateLimitError) and error.retry_after is not None else min(self.config.backoff_max_seconds, self.config.backoff_seconds * (2 ** attempt))
                self._sleep(delay)
        raise AssertionError("unreachable")

    @staticmethod
    def _validate_messages(messages):
        if not messages:
            raise InvalidRequestError("messages must not be empty")
        for message in messages:
            if not message.role or not message.content:
                raise InvalidRequestError("each message requires a role and content")

    def _stream_event(self, raw: Any) -> LLMStreamEvent:
        def value(obj, key, default=None):
            if isinstance(obj, dict):
                return obj.get(key, default)
            return getattr(obj, key, default)

        event_type = value(raw, "type", "")
        # Chat Completions chunks
        choices = value(raw, "choices")
        if choices:
            choice = choices[0]
            delta = value(choice, "delta")
            content = value(delta, "content", "") if delta is not None else ""
            usage_raw = value(raw, "usage")
            usage = self._usage(usage_raw, prompt="prompt_tokens", completion="completion_tokens")
            finish_reason = value(choice, "finish_reason")
            return LLMStreamEvent("content_delta" if content else ("completed" if finish_reason else event_type), content or "", value(raw, "model"), usage, {"finish_reason": finish_reason})
        # Responses events expose output text in `delta`; response.completed carries usage.
        delta = value(raw, "delta", "")
        response = value(raw, "response")
        usage_raw = value(response, "usage") if response is not None else None
        usage = self._usage(usage_raw, prompt="input_tokens", completion="output_tokens")
        model = value(response, "model") if response is not None else None
        metadata = {"type": event_type} if event_type else {}
        if response is not None:
            metadata["status"] = value(response, "status")
            metadata["id"] = value(response, "id")
        return LLMStreamEvent("content_delta" if event_type == "response.output_text.delta" else ("completed" if event_type in ("response.completed", "response.done") else event_type), str(delta or ""), model, usage, metadata)

    @staticmethod
    def _usage(raw, prompt, completion):
        if raw is None:
            return None
        return Usage(getattr(raw, prompt, None), getattr(raw, completion, None), getattr(raw, "total_tokens", None))

    def _normalize(self, raw: Any) -> LLMResponse:
        if hasattr(raw, "choices"):
            message = raw.choices[0].message
            usage_raw = getattr(raw, "usage", None)
            usage = None if usage_raw is None else Usage(
                getattr(usage_raw, "prompt_tokens", None),
                getattr(usage_raw, "completion_tokens", None),
                getattr(usage_raw, "total_tokens", None),
            )
            return LLMResponse(
                getattr(message, "content", "") or "",
                getattr(raw, "model", self.config.model),
                usage,
                {"id": getattr(raw, "id", None), "finish_reason": getattr(raw.choices[0], "finish_reason", None), "refusal": getattr(message, "refusal", None)},
            )
        usage_raw = getattr(raw, "usage", None)
        usage = None if usage_raw is None else Usage(
            getattr(usage_raw, "input_tokens", None),
            getattr(usage_raw, "output_tokens", None),
            getattr(usage_raw, "total_tokens", None),
        )
        content = getattr(raw, "output_text", "") or ""
        metadata = {
            "id": getattr(raw, "id", None),
            "status": getattr(raw, "status", None),
            "incomplete_details": getattr(raw, "incomplete_details", None),
        }
        return LLMResponse(content, getattr(raw, "model", self.config.model), usage, metadata)

    @staticmethod
    def _normalize_error(exc: Exception):
        name, text = exc.__class__.__name__.lower(), str(exc)
        if "authentication" in name or "permission" in name or "401" in text:
            return AuthenticationError("LLM authentication failed")
        if "ratelimit" in name or "rate limit" in text.lower() or "429" in text:
            return RateLimitError("LLM rate limit exceeded", getattr(exc, "retry_after", None))
        if "timeout" in name or "timed out" in text.lower():
            return TimeoutError("LLM request timed out")
        if "invalid" in name or "badrequest" in name or any(code in text for code in ("400", "404", "422")) or "model not found" in text.lower():
            return InvalidRequestError("LLM request was rejected")
        return UpstreamError("LLM upstream request failed")
