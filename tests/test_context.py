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
    assert data["vehicle_source"] is None
    assert data["cargo_profiles"] == []
    assert data["cargo_profile_summary"] is None


def test_order_context_serializes_derived_profiles_without_changing_raw_cargo():
    context = OrderContext(
        cargo=[{"name": "香蕉", "weight": ["1吨"], "quantity": [], "volume": [], "dimensions": []}],
        cargo_profiles=[{"name": "香蕉", "weight": {"total_kg": 1000, "basis": "explicit"}}],
        cargo_profile_summary={"total_weight_kg": 1000, "weight_status": "explicit"},
    )
    data = context.to_dict()
    assert data["cargo"] == context.cargo
    assert data["cargo_profiles"] == context.cargo_profiles
    assert data["cargo_profile_summary"] == context.cargo_profile_summary


def test_reducer_scalar_replace_and_remove_is_pure():
    original = OrderContext()
    reducer = OrderContextReducer()
    updated = reducer.apply(original, [Entity("location", "set", {"role": "pickup", "city": "上海"}), Entity("location", "replace", {"role": "pickup", "city": "杭州"})])
    assert updated.pickup_location["city"] == "杭州"
    assert original.pickup_location is None
    cleared = reducer.apply(updated, [Entity("location", "remove", {"role": "pickup", "city": "杭州"})])
    assert cleared.pickup_location is None


def test_reducer_preserves_location_city_and_full_address():
    context = OrderContextReducer().apply(
        OrderContext(),
        [
            Entity(
                "location",
                "set",
                {
                    "role": "pickup",
                    "city": "上海",
                    "full_address": "上海浦东金桥物流园3号仓库",
                },
            ),
            Entity(
                "location",
                "set",
                {
                    "role": "dropoff",
                    "city": "温州",
                    "full_address": "温州瓯海批发市场",
                },
            ),
        ],
    )
    assert context.pickup_location == {
        "role": "pickup",
        "city": "上海",
        "full_address": "上海浦东金桥物流园3号仓库",
    }
    assert context.dropoff_location == {
        "role": "dropoff",
        "city": "温州",
        "full_address": "温州瓯海批发市场",
    }


def test_reducer_cargo_add_and_remove():
    reducer = OrderContextReducer()
    first = reducer.apply(OrderContext(), [Entity("cargo", "set", {"name": "苹果", "weight": "2吨"})])
    second = reducer.apply(first, [Entity("cargo", "add", {"name": "苹果", "weight": "1吨"})])
    assert second.cargo == [{
        "name": "苹果",
        "weight": ["2吨", "1吨"],
        "quantity": [],
        "volume": [],
        "dimensions": [],
    }]
    removed = reducer.apply(second, [Entity("cargo", "remove", {"name": "苹果"})])
    assert removed.cargo == []


def test_reducer_cargo_replace_replaces_raw_lists():
    reducer = OrderContextReducer()
    context = reducer.apply(
        OrderContext(),
        [Entity("cargo", "set", {
            "name": "香蕉",
            "weight": "1吨",
            "quantity": "20箱",
            "volume": "5立方",
            "dimensions": "2米×1米×1米",
        })],
    )
    replaced = reducer.apply(
        context,
        [Entity("cargo", "replace", {"name": "香蕉", "weight": "500公斤"})],
    )
    assert replaced.cargo == [{
        "name": "香蕉",
        "weight": ["500公斤"],
        "quantity": [],
        "volume": [],
        "dimensions": [],
    }]


def test_reducer_cargo_ignores_null_and_empty_attributes():
    reducer = OrderContextReducer()
    context = reducer.apply(
        OrderContext(),
        [Entity("cargo", "set", {
            "name": "苹果",
            "weight": None,
            "quantity": "",
            "volume": [],
            "dimensions": " ",
        })],
    )
    assert context.cargo == [{
        "name": "苹果",
        "weight": [],
        "quantity": [],
        "volume": [],
        "dimensions": [],
    }]


def test_reducer_cargo_migrates_legacy_scalar_record_on_cargo_action():
    legacy = OrderContext(cargo=[{"name": "苹果", "weight": "1吨"}])
    updated = OrderContextReducer().apply(
        legacy,
        [Entity("cargo", "add", {"name": "香蕉", "weight": "500公斤"})],
    )
    assert updated.cargo == [
        {
            "name": "苹果",
            "weight": ["1吨"],
            "quantity": [],
            "volume": [],
            "dimensions": [],
        },
        {
            "name": "香蕉",
            "weight": ["500公斤"],
            "quantity": [],
            "volume": [],
            "dimensions": [],
        },
    ]
    assert legacy.cargo == [{"name": "苹果", "weight": "1吨"}]


def test_raw_cargo_context_serializes_as_json_compatible_lists():
    context = OrderContext(cargo=[{
        "name": "香蕉",
        "weight": ["1吨", "500公斤"],
        "quantity": [],
        "volume": [],
        "dimensions": [],
    }])
    assert context.to_dict()["cargo"] == [{
        "name": "香蕉",
        "weight": ["1吨", "500公斤"],
        "quantity": [],
        "volume": [],
        "dimensions": [],
    }]


def test_reducer_list_and_remark_actions():
    reducer = OrderContextReducer()
    context = reducer.apply(OrderContext(), [Entity("vehicle_specs", "set", {"extraction_text": "高顶"}), Entity("remark", "set", {"value": "易碎轻放"})])
    context = reducer.apply(context, [Entity("vehicle_specs", "add", {"extraction_text": "带尾板"}), Entity("remark", "add", {"value": "装货地电联"})])
    assert context.vehicle_specs == ["high_roof", "tail_lift"]
    assert context.remark == "易碎轻放;装货地电联"
    context = reducer.apply(context, [Entity("vehicle_specs", "replace", {"extraction_text": "封闭式"}), Entity("remark", "replace", {"value": "新备注"})])
    assert context.vehicle_specs == ["enclosed"]
    assert context.remark == "新备注"
