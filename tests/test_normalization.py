import pytest

from inorder_llm.context import OrderContext, OrderContextReducer
from inorder_llm.extract import Entity
from inorder_llm.normalization import NormalizationError, normalize_entities, normalize_entity


@pytest.mark.parametrize(
    ("entity_type", "raw", "expected"),
    [
        ("payment_type", "货到付款", 0),
        ("payment_type", "预付款", 1),
        ("invoice_type", "电子普通发票", 1),
        ("invoice_type", "纸质专票", 2),
        ("oneself_follow_flag", "我跟车", 1),
        ("oneself_follow_flag", "不跟车", 2),
        ("service_type", "快速送达", "express"),
        ("service_type", "加急", "urgent"),
        ("service_type", "用户议价", "user_bid"),
        ("service_type", "顺风拼车", "shared"),
    ],
)
def test_normalize_supported_aliases(entity_type, raw, expected):
    entity = normalize_entity(Entity(entity_type, "set", {"value": raw}, raw))
    assert entity.attributes["value"] == expected
    assert entity.attributes["raw"] == raw


@pytest.mark.parametrize(
    ("entity_type", "raw"),
    [
        ("payment_type", 0),
        ("invoice_type", 2),
        ("oneself_follow_flag", 1),
        ("service_type", "express"),
    ],
)
def test_normalize_is_idempotent(entity_type, raw):
    entity = normalize_entity(Entity(entity_type, "set", {"value": raw}, "原始表达"))
    assert normalize_entity(entity) == entity


def test_normalize_preserves_original_expression_on_repeat():
    entity = normalize_entity(Entity("service_type", "set", {"value": "快车"}, "快车"))
    repeated = normalize_entity(entity)
    assert repeated.attributes["value"] == "express"
    assert repeated.attributes["raw"] == "快车"
    assert repeated == entity


def test_unknown_enum_reports_context():
    with pytest.raises(NormalizationError) as exc_info:
        normalize_entity(Entity("payment_type", "set", {"value": "月结"}, "月结"))
    error = exc_info.value
    assert error.entity_type == "payment_type"
    assert error.raw_value == "月结"
    assert error.supported_values == (0, 1)


def test_non_enum_entities_pass_through_and_batch_is_pure():
    entity = Entity("cargo", "set", {"name": "苹果"}, "苹果")
    entities = [entity]
    result = normalize_entities(entities)
    assert result == entities
    assert result is not entities
    assert result[0] is entity


def test_reducer_normalizes_enum_before_writing_context():
    context = OrderContext()
    updated = OrderContextReducer().apply(
        context,
        [
            Entity("payment_type", "set", {"value": "提前付款"}, "提前付款"),
            Entity("service_type", "set", {"value": "快车"}, "快车"),
        ],
    )
    assert updated.payment_type == 1
    assert updated.service_type == "express"
    assert context.payment_type is None
    assert context.service_type is None
