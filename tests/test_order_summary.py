from inorder_llm.context import OrderContext
from inorder_llm.order_summary import build_order_summary


def _time():
    return {"context": "new_order", "start": "2026-08-28T10:00:00", "end": "2026-08-28T12:00:00"}


def _complete_context():
    return OrderContext(
        pickup_location={"city": "温州"},
        dropoff_location={"city": "上海"},
        cargo=[{"name": "苹果", "weight": ["1吨"], "quantity": [], "volume": [], "dimensions": []}],
        delivery_time=_time(),
    )


def test_complete_order_summary_contains_facts_and_ready_prompt():
    result = build_order_summary(_complete_context())
    assert result.status == "complete"
    assert result.missing_required == []
    assert "温州" in result.summary and "上海" in result.summary
    assert result.facts["cargo"][0]["name"] == "苹果"
    assert "准备好" in result.next_prompt
    assert result.user_message.startswith("已为您整理好这笔运输需求：")
    assert "重量为1吨" in result.user_message
    assert "complete" not in result.user_message


def test_missing_delivery_time_is_required_but_not_an_exception():
    context = _complete_context()
    context.delivery_time = None
    result = build_order_summary(context)
    assert result.status == "incomplete"
    assert [item.field for item in result.missing_required] == ["delivery_time"]
    assert "送达时间" in result.next_prompt
    assert result.user_message.startswith("目前已为您识别出：")
    assert "已识别从" not in result.user_message
    assert "例如“明天下午”或“8月28日10点”" in result.user_message
    assert "missing_required" not in result.user_message


def test_weight_or_quantity_is_one_combined_requirement():
    context = _complete_context()
    context.cargo = [{"name": "苹果", "weight": [], "quantity": [], "volume": [], "dimensions": []}]
    result = build_order_summary(context)
    assert [item.field for item in result.missing_required] == ["cargo.weight_or_quantity"]


def test_history_time_does_not_satisfy_delivery_time():
    context = _complete_context()
    context.delivery_time = {"context": "history", "start": "2026-08-20T00:00:00", "end": "2026-08-20T23:59:00"}
    result = build_order_summary(context)
    assert any(item.field == "delivery_time" for item in result.missing_required)


def test_vehicle_is_not_required_when_absent():
    result = build_order_summary(_complete_context())
    assert not any(item.field.startswith("vehicle") for item in result.missing_required)
