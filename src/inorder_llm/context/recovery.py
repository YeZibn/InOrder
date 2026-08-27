"""Pure helpers for recovering interrupted conversation turns."""

from copy import deepcopy
from dataclasses import dataclass
from typing import Any, Mapping

from .models import HistoryConversation

RETRY_COMMANDS = frozenset({"重试", "继续", "再试一次", "重新处理", "重来"})


def _copy_history(history: HistoryConversation) -> HistoryConversation:
    result = HistoryConversation()
    result.turns = deepcopy(history.turns)
    return result


@dataclass(frozen=True)
class ConversationRecovery:
    history: HistoryConversation
    message: str
    pending_messages: tuple[str, ...] = ()
    retry_requested: bool = False

    @property
    def recovered(self) -> bool:
        return bool(self.pending_messages)

    @property
    def is_retry(self) -> bool:
        return self.retry_requested

    def to_dict(self) -> dict[str, Any]:
        return {"recovered": self.recovered, "is_retry": self.is_retry, "pending_messages": list(self.pending_messages), "message": self.message, "history": self.history.to_dict()}

    def recovered_history(self, assistant_content: str, metadata: Mapping[str, Any] | None = None) -> HistoryConversation:
        result = _copy_history(self.history)
        result.append_user(self.message)
        if assistant_content:
            result.append_assistant(assistant_content, metadata)
        return result


def _pending_messages(history: HistoryConversation) -> tuple[str, ...]:
    last_assistant = max((i for i, turn in enumerate(history.turns) if turn.role == "assistant"), default=-1)
    return tuple(turn.content for turn in history.turns[last_assistant + 1:] if turn.role == "user" and turn.content)


def prepare_conversation_recovery(history: HistoryConversation, message: str) -> ConversationRecovery:
    if not message or not message.strip():
        raise ValueError("message must not be empty")
    source = _copy_history(history)
    pending = _pending_messages(source)
    current = message.strip()
    if not pending:
        return ConversationRecovery(source, current)
    if current in RETRY_COMMANDS:
        merged = "\n".join(pending)
    elif current == pending[-1] and len(pending) == 1:
        merged = pending[0]
    else:
        parts = list(pending)
        if current not in parts:
            parts.append(current)
        merged = "\n".join(parts)
    last_assistant = max((i for i, turn in enumerate(source.turns) if turn.role == "assistant"), default=-1)
    cleaned = HistoryConversation()
    cleaned.turns = deepcopy(source.turns[: last_assistant + 1])
    return ConversationRecovery(cleaned, merged, pending, current in RETRY_COMMANDS)


__all__ = ["RETRY_COMMANDS", "ConversationRecovery", "prepare_conversation_recovery"]
