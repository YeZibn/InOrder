from dataclasses import dataclass
from typing import Mapping, Optional, Tuple


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
