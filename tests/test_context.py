from inorder_llm.context import (ConversationSession, HistoryConversation, OrderContext,
                                 OrderContextReducer)
from inorder_llm.context.summary import summarize_assistant, to_data
from inorder_llm.extract.models import Entity
from inorder_llm.order_summary.models import OrderSummary


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
    assert data["reference_time"] is None
    assert data["pickup_location"] is None
    assert data["cargo"] == []
    assert data["vehicle_specs"] == []
    assert data["vehicle_source"] is None
    assert data["cargo_profiles"] == []
    assert data["cargo_profile_summary"] is None


def test_order_context_serializes_reference_time_and_accepts_legacy_shape():
    context = OrderContext(reference_time="2026-08-26 15:00")
    assert context.to_dict()["reference_time"] == "2026-08-26 15:00"


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
                    "province": "上海",
                    "city": "上海",
                    "full_address": "上海浦东金桥物流园3号仓库",
                },
            ),
            Entity(
                "location",
                "set",
                {
                    "role": "dropoff",
                    "province": "浙江",
                    "city": "温州",
                    "full_address": "温州瓯海批发市场",
                },
            ),
        ],
    )
    assert context.pickup_location == {
        "role": "pickup",
        "province": "上海",
        "city": "上海",
        "full_address": "上海浦东金桥物流园3号仓库",
    }
    assert context.dropoff_location == {
        "role": "dropoff",
        "province": "浙江",
        "city": "温州",
        "full_address": "温州瓯海批发市场",
    }


def test_vehicle_specs_updates_do_not_change_vehicle_source():
    context = OrderContext(vehicle_type="truck_5m2", vehicle_source="estimated")
    reducer = OrderContextReducer()

    updated = reducer.apply(
        context,
        [Entity("vehicle_specs", "set", {"value": "冷链"}, "冷链")],
    )

    assert updated.vehicle_type == "truck_5m2"
    assert updated.vehicle_source == "estimated"
    assert updated.vehicle_specs == ["cold_chain"]


def test_matched_vehicle_type_replaces_estimated_vehicle_and_source():
    context = OrderContext(vehicle_type="truck_5m2", vehicle_source="estimated")

    updated = OrderContextReducer().apply(
        context,
        [Entity("vehicle_type", "replace", {"value": "9米6"}, "换成9米6")],
    )

    assert updated.vehicle_type == "truck_9m6"
    assert updated.vehicle_source == "user_matched"


def test_unmatched_explicit_vehicle_replace_clears_previous_selection():
    context = OrderContext(vehicle_type="truck_4m2", vehicle_source="user_matched")

    updated = OrderContextReducer().apply(
        context,
        [Entity("vehicle_type", "replace", {"value": "大车"}, "换成大车")],
    )

    assert updated.vehicle_type is None
    assert updated.vehicle_source is None
    assert context.vehicle_type == "truck_4m2"


def test_unmatched_nonreplacement_vehicle_expression_preserves_context():
    context = OrderContext(vehicle_type="truck_4m2", vehicle_source="user_matched")

    updated = OrderContextReducer().apply(
        context,
        [Entity("vehicle_type", "set", {"value": "大车"}, "大车合适吗")],
    )

    assert updated.vehicle_type == "truck_4m2"
    assert updated.vehicle_source == "user_matched"


def test_vehicle_remove_clears_type_and_source_even_if_expression_is_unmatched():
    context = OrderContext(vehicle_type="truck_4m2", vehicle_source="user_matched")

    updated = OrderContextReducer().apply(
        context,
        [Entity(
            "vehicle_type",
            "remove",
            {"value": "未识别车型", "normalization_accepted": False},
            "车型不限",
        )],
    )

    assert updated.vehicle_type is None
    assert updated.vehicle_source is None


def test_legacy_vehicle_without_source_is_normalized_as_user_matched():
    context = OrderContext(vehicle_type="truck_4m2")

    updated = OrderContextReducer().apply(context, [])

    assert updated.vehicle_type == "truck_4m2"
    assert updated.vehicle_source == "user_matched"
    assert context.vehicle_source is None


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


def _order_summary(user_message="已为您整理好这笔运输需求：苹果从温州到上海"):
    return OrderSummary(
        status="complete",
        summary="已识别运输路线，货物为苹果。",
        missing_required=[],
        user_message=user_message,
    )


def test_to_data_converts_domain_objects_with_to_dict():
    summary = _order_summary()
    converted = to_data(summary)
    assert isinstance(converted, dict)
    assert to_data({"plain": "dict"}) == {"plain": "dict"}


def test_summarize_assistant_prefers_order_summary_from_dataclass():
    result = {
        "intent_result": {"main_intent": "order"},
        "order_result": {"order_summary": _order_summary()},
    }
    text, metadata = summarize_assistant(result)
    assert text == "已为您整理好这笔运输需求：苹果从温州到上海"
    assert metadata == {"main_intent": "order", "order_status": "complete"}


def test_summarize_assistant_reads_nested_order_result():
    result = {
        "intent_result": {"main_intent": "order"},
        "order_summary": {"user_message": "", "summary": "已识别运输路线。", "status": "incomplete"},
    }
    text, metadata = summarize_assistant(result)
    assert text == "已识别运输路线。"
    assert metadata["order_status"] == "incomplete"


def test_summarize_assistant_falls_back_to_intent_material():
    result = {"intent_result": {"main_intent": "qa"}, "order_graph_entered": False}
    text, metadata = summarize_assistant(result)
    assert text == "已完成意图识别：qa"
    assert metadata == {"main_intent": "qa"}


def test_summarize_assistant_bottom_fallback_without_extractable_content():
    text, metadata = summarize_assistant({})
    assert text == "已完成意图识别：未知"
    assert metadata == {}
    assert summarize_assistant("纯文本结果") == ("纯文本结果", {})


def test_reducer_list_and_remark_actions():
    reducer = OrderContextReducer()
    context = reducer.apply(OrderContext(), [Entity("vehicle_specs", "set", {"extraction_text": "高顶"}), Entity("remark", "set", {"value": "易碎轻放"})])
    context = reducer.apply(context, [Entity("vehicle_specs", "add", {"extraction_text": "带尾板"}), Entity("remark", "add", {"value": "装货地电联"})])
    assert context.vehicle_specs == ["high_roof", "tail_lift"]
    assert context.remark == "易碎轻放;装货地电联"
    context = reducer.apply(context, [Entity("vehicle_specs", "replace", {"extraction_text": "封闭式"}), Entity("remark", "replace", {"value": "新备注"})])
    assert context.vehicle_specs == ["enclosed"]
    assert context.remark == "新备注"
