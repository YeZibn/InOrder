from dataclasses import dataclass
from typing import Mapping, Optional


@dataclass(frozen=True)
class ChatMessage:
    role: str
    content: str


@dataclass(frozen=True)
class Usage:
    prompt_tokens: Optional[int] = None
    completion_tokens: Optional[int] = None
    total_tokens: Optional[int] = None


@dataclass(frozen=True)
class LLMResponse:
    text: str
    model: str
    usage: Optional[Usage] = None
    metadata: Optional[Mapping[str, object]] = None


@dataclass(frozen=True)
class LLMStreamEvent:
    """Provider-neutral event emitted while an LLM response is streaming."""

    event_type: str
    delta: str = ""
    model: Optional[str] = None
    usage: Optional[Usage] = None
    metadata: Optional[Mapping[str, object]] = None
