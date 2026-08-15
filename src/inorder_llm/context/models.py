"""Conversation and active order context domain models."""

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Literal, Mapping, Optional, Sequence

Role = Literal["user", "assistant", "system"]


def _json_value(value: Any) -> Any:
    if hasattr(value, "to_dict"):
        return value.to_dict()
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, list):
        return [_json_value(item) for item in value]
    if isinstance(value, tuple):
        return [_json_value(item) for item in value]
    if isinstance(value, dict):
        return {key: _json_value(item) for key, item in value.items()}
    return value


@dataclass(frozen=True)
class ConversationTurn:
    role: Role
    content: str
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {"role": self.role, "content": self.content, "created_at": self.created_at.isoformat(), "metadata": _json_value(dict(self.metadata))}


@dataclass
class HistoryConversation:
    turns: List[ConversationTurn] = field(default_factory=list)

    def append(self, role: Role, content: str, metadata: Optional[Mapping[str, Any]] = None) -> ConversationTurn:
        if not content:
            raise ValueError("conversation content must not be empty")
        turn = ConversationTurn(role, content, metadata=dict(metadata or {}))
        self.turns.append(turn)
        return turn

    def append_user(self, content: str, metadata: Optional[Mapping[str, Any]] = None) -> ConversationTurn:
        return self.append("user", content, metadata)

    def append_assistant(self, content: str, metadata: Optional[Mapping[str, Any]] = None) -> ConversationTurn:
        return self.append("assistant", content, metadata)

    def append_system(self, content: str, metadata: Optional[Mapping[str, Any]] = None) -> ConversationTurn:
        return self.append("system", content, metadata)

    def recent(self, limit: Optional[int] = None) -> List[ConversationTurn]:
        if limit is None:
            return list(self.turns)
        if limit < 0:
            raise ValueError("limit must not be negative")
        return list(self.turns[-limit:]) if limit else []

    def as_llm_messages(self, limit: Optional[int] = None) -> List[Dict[str, str]]:
        return [{"role": turn.role, "content": turn.content} for turn in self.recent(limit)]

    def to_dict(self) -> Dict[str, Any]:
        return {"turns": [turn.to_dict() for turn in self.turns]}


@dataclass
class OrderContext:
    pickup_location: Optional[Mapping[str, Any]] = None
    dropoff_location: Optional[Mapping[str, Any]] = None
    sender: Optional[Mapping[str, Any]] = None
    receiver: Optional[Mapping[str, Any]] = None
    sender_phone: Optional[str] = None
    receiver_phone: Optional[str] = None
    cargo: List[Dict[str, Any]] = field(default_factory=list)
    vehicle_type: Optional[str] = None
    vehicle_specs: List[str] = field(default_factory=list)
    delivery_time: Optional[Mapping[str, Any]] = None
    follow_car_number: Optional[int] = None
    oneself_follow_flag: Optional[int] = None
    invoice_type: Optional[int] = None
    payment_type: Optional[int] = None
    service_type: Optional[str] = None
    remark: Optional[str] = None
    referenced_order_id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return _json_value(asdict(self))


@dataclass
class ConversationSession:
    history: HistoryConversation = field(default_factory=HistoryConversation)
    order_context: OrderContext = field(default_factory=OrderContext)

    def to_dict(self) -> Dict[str, Any]:
        return {"history": self.history.to_dict(), "order_context": self.order_context.to_dict()}


__all__ = ["ConversationTurn", "HistoryConversation", "OrderContext", "ConversationSession"]
