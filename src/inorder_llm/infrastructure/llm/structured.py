"""Small helper for bounded structured-output repair retries."""

from typing import Callable, Sequence, TypeVar

from .models import ChatMessage

T = TypeVar("T")


def call_with_format_repair(client, messages: Sequence[ChatMessage], parser: Callable[[str], T], repair_instruction: str) -> T:
    """Parse one response and make at most one explicit format-repair request."""
    response = client.chat(messages)
    try:
        return parser(response.text)
    except Exception as first_error:
        try:
            repaired = client.chat([*messages, ChatMessage("user", repair_instruction)])
            return parser(repaired.text)
        except Exception:
            raise first_error


async def acall_with_format_repair(client, messages: Sequence[ChatMessage], parser: Callable[[str], T], repair_instruction: str, deadline_at: float = None) -> T:
    """Async equivalent; transport/deadline failures during repair propagate."""
    response = await client.achat(messages, deadline_at=deadline_at)
    try:
        return parser(response.text)
    except Exception:
        repaired = await client.achat([*messages, ChatMessage("user", repair_instruction)], deadline_at=deadline_at)
        return parser(repaired.text)
