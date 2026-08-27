from types import SimpleNamespace

import pytest

from inorder_llm.infrastructure.llm.client import LLMClient
from inorder_llm.infrastructure.llm.transport import OpenAITransport
from inorder_llm.infrastructure.llm.config import LLMConfig, load_config
from inorder_llm.infrastructure.llm.errors import AuthenticationError, ConfigurationError, RateLimitError, TimeoutError
from inorder_llm.infrastructure.llm.models import ChatMessage
from inorder_llm.infrastructure.llm.text import strip_json_prefix


def config(**kwargs):
    values = dict(api_key="secret", base_url="https://example.test/v1", model="demo", max_retries=2, backoff_seconds=0, api_mode="responses")
    values.update(kwargs)
    return LLMConfig(**values)


def response():
    return SimpleNamespace(model="demo", id="r1", output_text="hello", status="completed", usage=SimpleNamespace(input_tokens=2, output_tokens=3, total_tokens=5))


class FakeTransport:
    def __init__(self, result=None, errors=None):
        self.result, self.errors, self.calls = result, list(errors or []), []

    def complete(self, messages, config):
        self.calls.append((messages, config))
        if self.errors:
            raise self.errors.pop(0)
        return self.result

    def stream(self, messages, config):
        self.calls.append((messages, config))
        if self.errors:
            raise self.errors.pop(0)
        return iter(self.result or [])


class StreamEvent:
    def __init__(self, content=None, finish_reason=None, model="demo", usage=None):
        self.model = model
        self.choices = [SimpleNamespace(
            delta=SimpleNamespace(content=content),
            finish_reason=finish_reason,
        )]
        self.usage = usage


class ResponsesEvent:
    def __init__(self, event_type, delta="", model="demo", usage=None):
        self.type = event_type
        self.delta = delta
        self.response = SimpleNamespace(model=model, id="r1", status="completed", usage=usage)


def test_load_config_and_missing_values():
    loaded = load_config({"LLM_API_KEY": "k", "LLM_BASE_URL": "u", "LLM_MODEL": "m", "LLM_MAX_RETRIES": "3"})
    assert loaded.max_retries == 3
    assert loaded.backoff_max_seconds == 8.0
    assert loaded.workflow_timeout_seconds == 90.0
    with pytest.raises(ConfigurationError):
        load_config({"LLM_API_KEY": "k"})
    assert load_config({"LLM_API_KEY": "k", "LLM_BASE_URL": "u", "LLM_MODEL": "m", "LLM_REASONING_EFFORT": "high"}).reasoning_effort == "high"
    assert load_config({"LLM_API_KEY": "k", "LLM_BASE_URL": "u", "LLM_MODEL": "m", "LLM_REASONING_EFFORT": "max"}).reasoning_effort == "max"
    with pytest.raises(ConfigurationError):
        load_config({"LLM_API_KEY": "k", "LLM_BASE_URL": "u", "LLM_MODEL": "m", "LLM_REASONING_EFFORT": "xhigh"})
    assert load_config({"LLM_API_KEY": "k", "LLM_BASE_URL": "u", "LLM_MODEL": "m"}).api_mode == "chat_completions"
    assert load_config({"LLM_API_KEY": "k", "LLM_BASE_URL": "u", "LLM_MODEL": "m", "LLM_API_MODE": "responses"}).api_mode == "responses"
    assert load_config({"LLM_API_KEY": "k", "LLM_BASE_URL": "u", "LLM_MODEL": "m", "LLM_STREAMING": "true"}).streaming is True
    with pytest.raises(ConfigurationError):
        load_config({"LLM_API_KEY": "k", "LLM_BASE_URL": "u", "LLM_MODEL": "m", "LLM_API_MODE": "other"})
    with pytest.raises(ConfigurationError):
        load_config({"LLM_API_KEY": "k", "LLM_BASE_URL": "u", "LLM_MODEL": "m", "LLM_STREAMING": "sometimes"})


def test_provider_defaults_and_validation():
    openai = load_config({"LLM_API_KEY": "k", "LLM_MODEL": "m"})
    assert openai.provider == "openai"
    assert openai.base_url == "https://api.openai.com/v1"
    deepseek = load_config({"LLM_API_KEY": "k", "LLM_PROVIDER": "deepseek", "LLM_MODEL": "deepseek-chat"})
    assert deepseek.provider == "deepseek"
    assert deepseek.base_url == "https://api.deepseek.com"
    overridden = load_config({"LLM_API_KEY": "k", "LLM_PROVIDER": "deepseek", "LLM_BASE_URL": "https://gateway.test/v1", "LLM_MODEL": "m"})
    assert overridden.base_url == "https://gateway.test/v1"
    with pytest.raises(ConfigurationError):
        load_config({"LLM_API_KEY": "k", "LLM_MODEL": "m", "LLM_PROVIDER": "azure"})


def test_provider_specific_api_key_priority():
    # Provider-specific key takes priority over shared LLM_API_KEY
    cfg = load_config({
        "LLM_PROVIDER": "deepseek",
        "LLM_API_KEY": "shared-key",
        "LLM_API_KEY_DEEPSEEK": "deepseek-specific",
        "LLM_MODEL": "deepseek-v4-flash",
    })
    assert cfg.api_key == "deepseek-specific"

    cfg = load_config({
        "LLM_PROVIDER": "openai",
        "LLM_API_KEY": "shared-key",
        "LLM_API_KEY_OPENAI": "openai-specific",
        "LLM_MODEL": "gpt-4o-mini",
    })
    assert cfg.api_key == "openai-specific"


def test_provider_api_key_fallback_to_shared():
    # Falls back to LLM_API_KEY when provider-specific key is absent
    cfg = load_config({
        "LLM_PROVIDER": "deepseek",
        "LLM_API_KEY": "shared-key",
        "LLM_MODEL": "deepseek-v4-flash",
    })
    assert cfg.api_key == "shared-key"


def test_provider_api_key_missing_rejected():
    # Rejects when neither provider-specific key nor fallback is configured
    with pytest.raises(ConfigurationError):
        load_config({"LLM_PROVIDER": "deepseek", "LLM_MODEL": "deepseek-v4-flash"})
    with pytest.raises(ConfigurationError):
        load_config({"LLM_PROVIDER": "openai", "LLM_MODEL": "gpt-4o-mini"})


class _RecordingResource:
    def __init__(self):
        self.calls = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        return response()


def _transport_for_resource():
    transport = OpenAITransport.__new__(OpenAITransport)
    resource = _RecordingResource()
    transport._client = SimpleNamespace(
        chat=SimpleNamespace(completions=resource),
        responses=resource,
    )
    return transport, resource


def test_deepseek_chat_completions_request_shape():
    transport, resource = _transport_for_resource()
    cfg = config(provider="deepseek", api_mode="chat_completions", reasoning_effort="low")
    transport.complete([ChatMessage("system", "json"), ChatMessage("user", "hi")], cfg)
    request = resource.calls[0]
    assert request["messages"] == [{"role": "system", "content": "json"}, {"role": "user", "content": "hi"}]
    assert request["reasoning_effort"] == "low"
    assert "input" not in request and "reasoning" not in request


def test_deepseek_responses_request_shape():
    transport, resource = _transport_for_resource()
    cfg = config(provider="deepseek", api_mode="responses", reasoning_effort="high")
    transport.complete([ChatMessage("user", "hi")], cfg)
    request = resource.calls[0]
    assert request["input"] == [{"role": "user", "content": "hi"}]
    assert request["reasoning"] == {"effort": "high"}
    assert "messages" not in request and "reasoning_effort" not in request


def test_deepseek_stream_request_shapes():
    transport, resource = _transport_for_resource()
    chat_cfg = config(provider="deepseek", api_mode="chat_completions", reasoning_effort="high")
    transport.stream([ChatMessage("user", "hi")], chat_cfg)
    request = resource.calls[0]
    assert request["stream"] is True
    assert request["messages"] == [{"role": "user", "content": "hi"}]
    assert request["reasoning_effort"] == "high"

    resource.calls.clear()
    responses_cfg = config(provider="deepseek", api_mode="responses", reasoning_effort="low")
    transport.stream([ChatMessage("user", "hi")], responses_cfg)
    request = resource.calls[0]
    assert request["stream"] is True
    assert request["input"] == [{"role": "user", "content": "hi"}]
    assert request["reasoning"] == {"effort": "low"}


def test_success_normalizes_response_and_messages():
    transport = FakeTransport(response())
    result = LLMClient(config(), transport=transport).chat([ChatMessage("user", "hi")])
    assert result.text == "hello"
    assert result.usage.total_tokens == 5
    assert transport.calls[0][0][0].role == "user"


def test_content_observer_receives_each_normalized_response():
    transport = FakeTransport(response())
    contents = []
    LLMClient(config(), transport=transport, on_content=contents.append).chat([ChatMessage("user", "hi")])
    assert contents == ["hello"]


def test_normalized_response_exposes_finish_reason_and_refusal():
    raw = response()
    raw.incomplete_details = None
    result = LLMClient(config(), transport=FakeTransport(raw)).chat([ChatMessage("user", "hi")])
    assert result.metadata["status"] == "completed"
    assert result.metadata["incomplete_details"] is None


def test_empty_messages_are_rejected_without_transport_call():
    transport = FakeTransport(response())
    with pytest.raises(Exception):
        LLMClient(config(), transport=transport).chat([])
    assert not transport.calls


def test_timeout_retries_then_succeeds():
    transport = FakeTransport(response(), [TimeoutError("x")])
    result = LLMClient(config(), transport=transport).chat([ChatMessage("user", "hi")])
    assert result.text == "hello"
    assert len(transport.calls) == 2


def test_backoff_is_capped():
    transport = FakeTransport(errors=[TimeoutError("x"), TimeoutError("x"), TimeoutError("x")])
    sleeps = []
    with pytest.raises(TimeoutError):
        LLMClient(config(max_retries=2, backoff_seconds=10, backoff_max_seconds=3), transport=transport, sleep=sleeps.append).chat([ChatMessage("user", "hi")])
    assert sleeps == [3, 3]


def test_authentication_does_not_retry_or_leak_secret():
    transport = FakeTransport(errors=[Exception("secret 401")])
    with pytest.raises(AuthenticationError) as caught:
        LLMClient(config(), transport=transport).chat([ChatMessage("user", "hi")])
    assert len(transport.calls) == 1
    assert "secret" not in str(caught.value)


def test_rate_limit_exposes_retry_after():
    class RateLimitErrorFromProvider(Exception):
        retry_after = 0
    transport = FakeTransport(response(), [RateLimitErrorFromProvider("429")])
    result = LLMClient(config(), transport=transport).chat([ChatMessage("user", "hi")])
    assert result.text == "hello"


def test_reasoning_effort_is_available_to_injected_transport():
    transport = FakeTransport(response())
    LLMClient(config(reasoning_effort="medium"), transport=transport).chat([ChatMessage("user", "hi")])
    assert transport.calls[0][1].reasoning_effort == "medium"


def test_reasoning_effort_can_be_omitted():
    transport = FakeTransport(response())
    LLMClient(config(), transport=transport).chat([ChatMessage("user", "hi")])
    assert transport.calls[0][1].reasoning_effort is None


def test_stream_accumulates_chat_content_and_calls_delta_observer():
    transport = FakeTransport([
        StreamEvent("hel"), StreamEvent("lo"), StreamEvent("", "stop"),
    ])
    deltas = []
    result = LLMClient(config(), transport=transport).stream([ChatMessage("user", "hi")], deltas.append)
    assert result.text == "hello"
    assert deltas == ["hel", "lo"]


def test_stream_accumulates_responses_content():
    transport = FakeTransport([
        ResponsesEvent("response.output_text.delta", "hel"),
        ResponsesEvent("response.output_text.delta", "lo"),
        ResponsesEvent("response.completed"),
    ])
    result = LLMClient(config(), transport=transport).stream([ChatMessage("user", "hi")])
    assert result.text == "hello"


def test_stream_accepts_mapping_events():
    transport = FakeTransport([
        {"choices": [{"delta": {"content": "ok"}, "finish_reason": None}], "model": "demo"},
        {"choices": [{"delta": {"content": ""}, "finish_reason": "stop"}], "model": "demo"},
    ])
    assert LLMClient(config(), transport=transport).stream([ChatMessage("user", "hi")]).text == "ok"


def test_stream_retries_before_first_delta():
    transport = FakeTransport([StreamEvent("ok")], [TimeoutError("x")])
    result = LLMClient(config(), transport=transport).stream([ChatMessage("user", "hi")])
    assert result.text == "ok"
    assert len(transport.calls) == 2


def test_stream_excludes_reasoning_deltas_from_text_and_callback():
    transport = FakeTransport([
        ResponsesEvent("response.reasoning_text.delta", "thinking..."),
        ResponsesEvent("response.output_text.delta", '{"a": '),
        ResponsesEvent("response.output_text.delta", "1}"),
        ResponsesEvent("response.completed"),
    ])
    deltas = []
    result = LLMClient(config(), transport=transport).stream([ChatMessage("user", "hi")], deltas.append)
    assert result.text == '{"a": 1}'
    assert deltas == ['{"a": ', "1}"]


def test_stream_allows_retry_after_reasoning_only_delta():
    # Reasoning deltas must not count as delivered content:
    # a retryable error after only reasoning output still retries.
    class ReasoningThenError:
        def __iter__(self):
            yield ResponsesEvent("response.reasoning_text.delta", "thinking...")
            raise TimeoutError("x")
    transport = FakeTransport([StreamEvent("ok")], None)

    def stream(messages, config):
        transport.calls.append((messages, config))
        if len(transport.calls) == 1:
            return iter(ReasoningThenError())
        return iter([StreamEvent("ok")])

    transport.stream = stream
    result = LLMClient(config(), transport=transport).stream([ChatMessage("user", "hi")])
    assert result.text == "ok"
    assert len(transport.calls) == 2


def test_stream_does_not_retry_after_delta():
    class BrokenIterator:
        def __iter__(self):
            yield StreamEvent("partial")
            raise TimeoutError("broken")
    class BrokenTransport(FakeTransport):
        def stream(self, messages, config):
            self.calls.append((messages, config))
            return BrokenIterator()
    transport = BrokenTransport()
    with pytest.raises(TimeoutError):
        LLMClient(config(), transport=transport).stream([ChatMessage("user", "hi")])
    assert len(transport.calls) == 1


def test_strip_json_prefix_only_removes_leading_invisible_characters():
    assert strip_json_prefix("\ufeff\u200b{\"ok\":true}") == '{"ok":true}'
    inner = '{"value":"\u200b"}'
    assert strip_json_prefix(inner) == inner
