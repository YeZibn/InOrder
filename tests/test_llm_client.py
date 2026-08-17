from types import SimpleNamespace

import pytest

from inorder_llm.infrastructure.llm.client import LLMClient
from inorder_llm.infrastructure.llm.config import LLMConfig, load_config
from inorder_llm.infrastructure.llm.errors import AuthenticationError, ConfigurationError, RateLimitError, TimeoutError
from inorder_llm.infrastructure.llm.models import ChatMessage


def config(**kwargs):
    values = dict(api_key="secret", base_url="https://example.test/v1", model="demo", max_retries=2, backoff_seconds=0)
    values.update(kwargs)
    return LLMConfig(**values)


def response():
    return SimpleNamespace(model="demo", id="r1", choices=[SimpleNamespace(message=SimpleNamespace(content="hello"))], usage=SimpleNamespace(prompt_tokens=2, completion_tokens=3, total_tokens=5))


class FakeTransport:
    def __init__(self, result=None, errors=None):
        self.result, self.errors, self.calls = result, list(errors or []), []

    def complete(self, messages, config):
        self.calls.append((messages, config))
        if self.errors:
            raise self.errors.pop(0)
        return self.result


def test_load_config_and_missing_values():
    loaded = load_config({"LLM_API_KEY": "k", "LLM_BASE_URL": "u", "LLM_MODEL": "m", "LLM_MAX_RETRIES": "3"})
    assert loaded.max_retries == 3
    with pytest.raises(ConfigurationError):
        load_config({"LLM_API_KEY": "k"})
    assert load_config({"LLM_API_KEY": "k", "LLM_BASE_URL": "u", "LLM_MODEL": "m", "LLM_REASONING_EFFORT": "high"}).reasoning_effort == "high"
    with pytest.raises(ConfigurationError):
        load_config({"LLM_API_KEY": "k", "LLM_BASE_URL": "u", "LLM_MODEL": "m", "LLM_REASONING_EFFORT": "max"})


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
    raw.choices[0].finish_reason = "stop"
    raw.choices[0].message.refusal = None
    result = LLMClient(config(), transport=FakeTransport(raw)).chat([ChatMessage("user", "hi")])
    assert result.metadata["finish_reason"] == "stop"
    assert result.metadata["refusal"] is None


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
