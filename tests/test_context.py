from inorder_llm.context import (ConversationSession, HistoryConversation, OrderContext,
                                 OrderContextReducer)
from inorder_llm.extract.models import Entity


def test_history_conversation_and_session():
    history = HistoryConversation()
    history.append_user("我要下单")
    history.append_assistant("好的")
    assert history.as_llm_messages() == [{"role": "user", "content": "我要下单"}, {"role": "assistant", "content": "好的"}]
    assert history.recent(1)[0].content == "好的"
    session = ConversationSession(history=history)
    assert session.order_context.to_dict()["cargo"] == []


def test_empty_order_context_is_json_compatible():
    data = OrderContext().to_dict()
    assert data["pickup_location"] is None
    assert data["cargo"] == []
    assert data["vehicle_specs"] == []


def test_reducer_scalar_replace_and_remove_is_pure():
    original = OrderContext()
    reducer = OrderContextReducer()
    updated = reducer.apply(original, [Entity("location", "set", {"role": "pickup", "city": "上海"}), Entity("location", "replace", {"role": "pickup", "city": "杭州"})])
    assert updated.pickup_location["city"] == "杭州"
    assert original.pickup_location is None
    cleared = reducer.apply(updated, [Entity("location", "remove", {"role": "pickup", "city": "杭州"})])
    assert cleared.pickup_location is None


def test_reducer_cargo_add_and_remove():
    reducer = OrderContextReducer()
    first = reducer.apply(OrderContext(), [Entity("cargo", "set", {"name": "苹果", "weight": "2吨"})])
    second = reducer.apply(first, [Entity("cargo", "add", {"name": "苹果", "weight": "1吨"})])
    assert second.cargo[0]["weight"] == "3吨"
    removed = reducer.apply(second, [Entity("cargo", "remove", {"name": "苹果"})])
    assert removed.cargo == []


def test_reducer_list_and_remark_actions():
    reducer = OrderContextReducer()
    context = reducer.apply(OrderContext(), [Entity("vehicle_specs", "set", {"extraction_text": "高顶"}), Entity("remark", "set", {"value": "易碎轻放"})])
    context = reducer.apply(context, [Entity("vehicle_specs", "add", {"extraction_text": "带尾板"}), Entity("remark", "add", {"value": "装货地电联"})])
    assert context.vehicle_specs == ["高顶", "带尾板"]
    assert context.remark == "易碎轻放;装货地电联"
    context = reducer.apply(context, [Entity("vehicle_specs", "replace", {"extraction_text": "封闭式"}), Entity("remark", "replace", {"value": "新备注"})])
    assert context.vehicle_specs == ["封闭式"]
    assert context.remark == "新备注"
