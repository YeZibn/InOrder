import pytest

from inorder_llm.context import ContextReductionError, OrderContext, OrderContextReducer
from inorder_llm.extract import Entity
from inorder_llm.normalization import PhoneNormalizationError, normalize_phone_entity


@pytest.mark.parametrize("raw", [
    "13800138000",
    "138 0013 8000",
    "138-0013-8000",
    "+86 138 0013 8000",
    "0086-138-0013-8000",
])
def test_normalize_supported_phone_formats(raw):
    result = normalize_phone_entity(Entity("phone", "set", {}, raw))
    assert result.attributes["value"] == "13800138000"
    assert result.attributes["raw"] == raw


@pytest.mark.parametrize("raw", [
    "1380013800",
    "138001380000",
    "12800138000",
    "13800abc8000",
    "+8813800138000",
])
def test_invalid_phone_is_rejected(raw):
    with pytest.raises(PhoneNormalizationError) as exc_info:
        normalize_phone_entity(Entity("phone", "set", {}, raw))
    assert exc_info.value.raw_value == raw


def test_phone_normalization_is_pure_and_idempotent():
    entity = Entity("phone", "set", {"value": "138 0013 8000"}, "原文")
    result = normalize_phone_entity(entity)
    assert dict(entity.attributes) == {"value": "138 0013 8000"}
    assert normalize_phone_entity(result) == result


def test_reducer_normalizes_sender_and_receiver_phone():
    updated = OrderContextReducer().apply(OrderContext(), [
        Entity("phone", "set", {"role": "sender"}, "138 0013 8000"),
        Entity("phone", "replace", {"role": "receiver", "value": "+86 13900139000"}, "原文"),
    ])
    assert updated.sender_phone == "13800138000"
    assert updated.receiver_phone == "13900139000"


def test_phone_add_is_rejected_and_remove_is_unchanged():
    with pytest.raises(ContextReductionError, match="add is not supported"):
        OrderContextReducer().apply(OrderContext(), [Entity("phone", "add", {"role": "sender"}, "13800138000")])
    context = OrderContext(sender_phone="13800138000")
    updated = OrderContextReducer().apply(context, [Entity("phone", "remove", {"role": "sender"}, "13800138000")])
    assert updated.sender_phone is None


def test_non_phone_entity_is_not_changed():
    entity = Entity("cargo", "set", {"name": "苹果"}, "苹果")
    assert normalize_phone_entity(entity) is entity
