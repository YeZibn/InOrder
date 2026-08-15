import pytest

from inorder_llm.context import ContextReductionError, OrderContext, OrderContextReducer
from inorder_llm.extract import Entity
from inorder_llm.normalization import TimeNormalizationError, normalize_time_entity


def _time(attrs, text="时间"):
    return Entity("time", "set", attrs, text)


def test_fixed_time_is_classified_and_timezone_added():
    result = normalize_time_entity(
        _time({"context": "new_order", "start": "2026-08-16 15:00", "end": "2026-08-16 15:00"}, "明天下午三点")
    )
    assert result.attributes["kind"] == "fixed"
    assert result.attributes["start"] == "2026-08-16T15:00:00+08:00"
    assert result.attributes["end"] == result.attributes["start"]
    assert result.attributes["timezone"] == "Asia/Shanghai"
    assert result.attributes["raw"] == "明天下午三点"


def test_closed_range_and_open_range_are_supported():
    closed = normalize_time_entity(_time({"context": "new_order", "start": "2026-08-16 06:00", "end": "2026-08-16 12:00"}))
    open_ended = normalize_time_entity(_time({"context": "history", "start": "", "end": "2026-08-16 12:00"}))
    assert closed.attributes["kind"] == "range"
    assert open_ended.attributes["kind"] == "range"
    assert open_ended.attributes["start"] is None


@pytest.mark.parametrize(
    "attrs",
    [
        {"context": "new_order", "start": "", "end": ""},
        {"context": "new_order", "start": "not-time", "end": "2026-08-16 12:00"},
        {"context": "new_order", "start": "2026-08-16 13:00", "end": "2026-08-16 12:00"},
        {"context": "other", "start": "2026-08-16 12:00", "end": "2026-08-16 12:00"},
    ],
)
def test_invalid_time_is_rejected(attrs):
    with pytest.raises(TimeNormalizationError):
        normalize_time_entity(_time(attrs))


def test_time_normalization_is_pure():
    entity = _time({"context": "new_order", "start": "2026-08-16 12:00", "end": "2026-08-16 12:00"})
    original = dict(entity.attributes)
    normalize_time_entity(entity)
    assert dict(entity.attributes) == original


def test_reducer_accepts_new_order_time_and_rejects_history_time():
    reducer = OrderContextReducer()
    updated = reducer.apply(
        OrderContext(),
        [_time({"context": "new_order", "start": "2026-08-16 12:00", "end": "2026-08-16 12:00"})],
    )
    assert updated.delivery_time["kind"] == "fixed"
    with pytest.raises(ContextReductionError, match="history time"):
        reducer.apply(
            updated,
            [_time({"context": "history", "start": "2026-08-15 00:00", "end": "2026-08-15 23:59"})],
        )
    assert updated.delivery_time["context"] == "new_order"
