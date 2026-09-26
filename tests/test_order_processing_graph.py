from copy import deepcopy

import pytest

from inorder_llm.context import ContextReductionError, OrderContextReducer
from inorder_llm.cargo_profile import parse_cargo_profile_from_text
from inorder_llm.context.models import HistoryConversation, OrderContext
from inorder_llm.extract.models import Entity
from inorder_llm.graph.order import build_order_processing_graph
from inorder_llm.intent.resolver import StructuredIntentError
from inorder_llm.rewrite.models import RewriteResult
from inorder_llm.vehicle_resolution import VehicleResolutionResult


class FakeRewriteModel:
    def __init__(self, result):
        self.result = result
        self.calls = []

    def rewrite(self, message, history, order_context):
        self.calls.append((message, history, order_context))
        return self.result


class FakeExtractor:
    def __init__(self, entities=None, error=None):
        self.entities = list(entities or [])
        self.error = error
        self.calls = []

    def extract(self, message, reference_time):
        self.calls.append((message, reference_time))
        if self.error:
            raise self.error
        return self.entities


class FakeCargoProfile:
    def __init__(self, result=None, error=None):
        self.result = result
        self.error = error
        self.calls = []

    def profile(self, cargo):
        self.calls.append(deepcopy(cargo))
        if self.error:
            raise self.error
        return self.result


class FakeVehicleResolution:
    def __init__(self, result):
        self.result = result
        self.calls = []

    def resolve(self, cargo_profiles, summary, raw_vehicle_text=None, effective_city=None, vehicle_specs=()):
        self.calls.append((
            deepcopy(cargo_profiles),
            deepcopy(summary),
            raw_vehicle_text,
            effective_city,
            list(vehicle_specs),
        ))
        return self.result


def _cargo_profile_result(name="香蕉"):
    return parse_cargo_profile_from_text(__import__("json").dumps({
        "cargo_profiles": [{
            "name": name,
            "weight_kg": 1000, "volume_m3": 1.8,
            "dimensions_cm": {"length": 120, "width": 100, "height": 150},
            "stackability": "partial", "fragility": "low", "temperature": "ambient",
            "reason": "重量由用户提供，体积和尺寸按常见包装估算。",
        }],
        "cargo_profile_summary": {"total_weight_kg": 1000, "total_volume_m3": 1.8, "reason": "根据画像汇总。"},
    }, ensure_ascii=False))


def _state(history=None, context=None):
    history = history or HistoryConversation()
    context = context or OrderContext()
    return {
        "message": "再加一吨苹果",
        "reference_time": "2026-08-17 10:00",
        "history": history,
        "order_context": context,
    }


def test_order_processing_graph_rewrites_then_extracts_incremental_text():
    history = HistoryConversation()
    history.append_user("当前订单已有一吨苹果")
    context = OrderContext(cargo=[{"name": "苹果", "weight": "1吨"}])
    rewrite = FakeRewriteModel(
        RewriteResult("已有一吨苹果，本轮再增加一吨苹果", "再加一吨苹果")
    )
    extractor = FakeExtractor(
        [Entity("cargo", "add", {"name": "苹果", "weight": "1吨"}, "一吨苹果")]
    )

    result = build_order_processing_graph(rewrite, extractor).invoke(
        _state(history, context)
    )

    assert result["rewrite_result"].extraction_text == "再加一吨苹果"
    assert result["entities"] == extractor.entities
    assert len(rewrite.calls) == 1
    assert len(extractor.calls) == 1
    assert extractor.calls[0][0] == "再加一吨苹果"
    assert extractor.calls[0][1] == "2026-08-17 10:00"
    assert result["order_summary"].status == "incomplete"
    assert any(item.field == "pickup_location" for item in result["order_summary"].missing_required)


def test_matched_user_vehicle_short_circuits_estimation():
    rewrite = FakeRewriteModel(RewriteResult("设置4米2", "设置4米2"))
    extractor = FakeExtractor([Entity("vehicle_type", "set", {"value": "4米2"}, "4米2")])
    estimator = FakeVehicleResolution(VehicleResolutionResult("truck_5m2", [], "estimated", "不应调用"))
    result = build_order_processing_graph(rewrite, extractor, vehicle_model=estimator).invoke(_state())
    assert result["vehicle_resolution"].vehicle_type == "truck_4m2"
    assert result["vehicle_resolution"].source == "user_matched"
    assert estimator.calls == []


def test_removing_user_vehicle_runs_estimation_and_keeps_specs():
    rewrite = FakeRewriteModel(RewriteResult("重新推荐车型", "移除当前车型"))
    extractor = FakeExtractor([Entity("vehicle_type", "remove", {"value": "4米2"}, "当前车型")])
    estimator = FakeVehicleResolution(VehicleResolutionResult(
        "truck_6m8", ["cold_chain"], "estimated", "下界通过。",
        candidates=[{"vehicle_type": "truck_6m8", "vehicle_specs": [], "fit_level": "lower_bound_fit"}],
    ))
    existing = OrderContext(
        vehicle_type="truck_4m2",
        vehicle_source="user_matched",
        vehicle_specs=["cold_chain"],
        cargo_profiles=[{"name": "苹果"}],
        cargo_profile_summary={"total_weight_kg": 1000},
    )

    result = build_order_processing_graph(rewrite, extractor, vehicle_model=estimator).invoke(
        _state(context=existing)
    )

    assert len(estimator.calls) == 1
    assert estimator.calls[0][4] == ["cold_chain"]
    assert result["order_context"].vehicle_type == "truck_6m8"
    assert result["order_context"].vehicle_source == "estimated"
    assert result["order_context"].vehicle_specs == ["cold_chain"]


def test_unmatched_vehicle_falls_back_to_estimation():
    rewrite = FakeRewriteModel(RewriteResult("换成大车", "换成大车"))
    extractor = FakeExtractor([Entity("vehicle_type", "replace", {}, "大车")])
    estimator = FakeVehicleResolution(VehicleResolutionResult(
        "", [], "estimated", "大车无法唯一匹配，只有上界候选。",
        candidates=[{"vehicle_type": "truck_6m8", "vehicle_specs": [], "fit_level": "upper_bound_only"}],
    ))
    existing = OrderContext(vehicle_type="truck_5m2", vehicle_specs=["cold_chain"], vehicle_source="user_matched")
    result = build_order_processing_graph(rewrite, extractor, vehicle_model=estimator).invoke(_state(context=existing))
    assert result["vehicle_resolution"].vehicle_type == ""
    assert result["vehicle_resolution"].source == "estimated"
    assert result["vehicle_resolution"].candidates[0]["fit_level"] == "upper_bound_only"
    assert estimator.calls[0][2] == "大车"
    assert estimator.calls[0][4] == ["cold_chain"]
    assert result["order_context"].vehicle_type is None
    assert result["order_context"].vehicle_specs == ["cold_chain"]
    assert result["order_context"].vehicle_source is None


def test_unmatched_nonreplacement_expression_preserves_user_vehicle():
    rewrite = FakeRewriteModel(RewriteResult("大车怎么样", "大车怎么样"))
    extractor = FakeExtractor([Entity("vehicle_type", "set", {"value": "大车"}, "大车怎么样")])
    estimator = FakeVehicleResolution(VehicleResolutionResult("truck_6m8", [], "estimated", "不应调用"))
    existing = OrderContext(vehicle_type="truck_4m2", vehicle_source="user_matched")

    result = build_order_processing_graph(rewrite, extractor, vehicle_model=estimator).invoke(
        _state(context=existing)
    )

    assert estimator.calls == []
    assert result["order_context"].vehicle_type == "truck_4m2"
    assert result["order_context"].vehicle_source == "user_matched"
    assert result["vehicle_resolution"].raw_vehicle_text == "大车怎么样"


def test_user_vehicle_stays_locked_when_cargo_changes():
    rewrite = FakeRewriteModel(RewriteResult("再加一吨苹果", "再加一吨苹果"))
    extractor = FakeExtractor([Entity("cargo", "add", {"name": "苹果", "weight": "1吨"}, "一吨苹果")])
    profile = FakeCargoProfile(_cargo_profile_result())
    estimator = FakeVehicleResolution(VehicleResolutionResult("truck_6m8", [], "estimated", "不应调用"))
    existing = OrderContext(
        vehicle_type="truck_4m2",
        vehicle_source="user_matched",
        cargo=[{"name": "苹果", "weight": ["1吨"], "quantity": [], "volume": [], "dimensions": []}],
    )

    result = build_order_processing_graph(
        rewrite, extractor, profile, vehicle_model=estimator
    ).invoke(_state(context=existing))

    assert len(profile.calls) == 1
    assert estimator.calls == []
    assert result["order_context"].vehicle_type == "truck_4m2"
    assert result["order_context"].vehicle_source == "user_matched"


def test_new_matched_vehicle_replaces_previous_estimate():
    rewrite = FakeRewriteModel(RewriteResult("还是用4米2", "还是用4米2"))
    extractor = FakeExtractor([Entity("vehicle_type", "replace", {"value": "4米2"}, "4米2")])
    estimator = FakeVehicleResolution(VehicleResolutionResult("truck_6m8", [], "estimated", "不应调用"))
    existing = OrderContext(vehicle_type="truck_7m6", vehicle_source="estimated")

    result = build_order_processing_graph(rewrite, extractor, vehicle_model=estimator).invoke(
        _state(context=existing)
    )

    assert estimator.calls == []
    assert result["order_context"].vehicle_type == "truck_4m2"
    assert result["order_context"].vehicle_source == "user_matched"


def test_estimated_vehicle_is_recomputed_after_cargo_change():
    rewrite = FakeRewriteModel(RewriteResult("把苹果增加到两吨", "苹果增加到两吨"))
    extractor = FakeExtractor([Entity("cargo", "replace", {"name": "苹果", "weight": "2吨"}, "两吨苹果")])
    profile_result = _cargo_profile_result("新苹果")
    profile = FakeCargoProfile(profile_result)
    estimator = FakeVehicleResolution(VehicleResolutionResult(
        "truck_6m8", [], "estimated", "新货物的下界候选通过。",
        candidates=[{"vehicle_type": "truck_6m8", "vehicle_specs": [], "fit_level": "lower_bound_fit"}],
    ))
    existing = OrderContext(
        vehicle_type="truck_4m2",
        vehicle_specs=["tail_lift"],
        vehicle_source="estimated",
        cargo=[{"name": "苹果", "weight": ["1吨"], "quantity": [], "volume": [], "dimensions": []}],
        cargo_profiles=[{"name": "旧苹果"}],
        cargo_profile_summary={"total_weight_kg": 1000},
    )

    result = build_order_processing_graph(
        rewrite, extractor, profile, estimator
    ).invoke(_state(context=existing))

    assert profile.calls[0][0]["weight"] == ["2吨"]
    assert estimator.calls[0][0] == [item.to_dict() for item in profile_result.cargo_profiles]
    assert estimator.calls[0][4] == ["tail_lift"]
    assert result["order_context"].vehicle_type == "truck_6m8"
    assert result["order_context"].vehicle_source == "estimated"
    assert result["order_context"].vehicle_specs == ["tail_lift"]


def test_estimated_vehicle_clears_when_recomputation_has_no_primary():
    rewrite = FakeRewriteModel(RewriteResult("重新核算车型", "重新核算车型"))
    extractor = FakeExtractor()
    estimator = FakeVehicleResolution(VehicleResolutionResult(
        "", [], "estimated", "只有上界候选。",
        candidates=[{"vehicle_type": "truck_6m8", "vehicle_specs": [], "fit_level": "upper_bound_only"}],
    ))
    existing = OrderContext(
        vehicle_type="truck_4m2",
        vehicle_specs=["cold_chain"],
        vehicle_source="estimated",
    )

    result = build_order_processing_graph(rewrite, extractor, vehicle_model=estimator).invoke(
        _state(context=existing)
    )

    assert result["vehicle_resolution"].vehicle_type == ""
    assert result["vehicle_resolution"].candidates[0]["fit_level"] == "upper_bound_only"
    assert result["order_context"].vehicle_type is None
    assert result["order_context"].vehicle_source is None
    assert result["order_context"].vehicle_specs == ["cold_chain"]


def test_estimate_receives_current_pickup_city_and_user_specs():
    rewrite = FakeRewriteModel(RewriteResult("起点改杭州，需要冷链和尾板", "起点改杭州，需要尾板"))
    extractor = FakeExtractor([
        Entity("location", "replace", {"role": "pickup", "city": "杭州"}, "杭州"),
        Entity("vehicle_specs", "add", {"value": "尾板"}, "尾板"),
    ])
    estimator = FakeVehicleResolution(VehicleResolutionResult(
        "truck_6m8", [], "estimated", "下界通过。",
        candidates=[{"vehicle_type": "truck_6m8", "vehicle_specs": [], "fit_level": "lower_bound_fit"}],
    ))
    existing = OrderContext(
        vehicle_type="truck_5m2",
        vehicle_specs=["cold_chain"],
        vehicle_source="estimated",
        pickup_location={"city": "上海"},
    )

    result = build_order_processing_graph(rewrite, extractor, vehicle_model=estimator).invoke(
        _state(context=existing)
    )

    assert estimator.calls[0][3] == "杭州"
    assert estimator.calls[0][4] == ["cold_chain", "tail_lift"]
    assert result["vehicle_resolution"].vehicle_specs == ["cold_chain", "tail_lift"]
    assert result["order_context"].vehicle_specs == ["cold_chain", "tail_lift"]


def test_estimated_lower_bound_candidate_is_committed_as_primary_vehicle():
    rewrite = FakeRewriteModel(RewriteResult("识别订单", "识别订单"))
    extractor = FakeExtractor()
    estimator = FakeVehicleResolution(VehicleResolutionResult(
        "truck_6m8", [], "estimated", "下界候选通过。",
        candidates=[{"vehicle_type": "truck_6m8", "vehicle_specs": ["cold_chain"], "fit_level": "lower_bound_fit"}],
    ))

    result = build_order_processing_graph(rewrite, extractor, vehicle_model=estimator).invoke(_state())

    assert result["vehicle_resolution"].vehicle_type == "truck_6m8"
    assert result["order_context"].vehicle_type == "truck_6m8"
    assert result["vehicle_resolution"].vehicle_specs == ["cold_chain"]
    assert result["order_context"].vehicle_specs == []
    assert result["order_context"].vehicle_source == "estimated"


def test_ambiguous_rewrite_still_calls_extractor():
    rewrite = FakeRewriteModel(
        RewriteResult("根据当前上下文选择最合理车型", "设置当前车型")
    )
    extractor = FakeExtractor([Entity("vehicle_type", "set", {}, "4米2")])

    result = build_order_processing_graph(rewrite, extractor).invoke(_state())

    assert result["entities"] == extractor.entities
    assert extractor.calls[0][0] == "设置当前车型"


def test_graph_preserves_history_and_order_context():
    history = HistoryConversation()
    history.append_user("从上海发货")
    context = OrderContext(pickup_location={"city": "上海"})
    history_before = deepcopy(history.to_dict())
    context_before = deepcopy(context.to_dict())
    rewrite = FakeRewriteModel(RewriteResult("本轮新增一吨苹果", "再加一吨苹果"))
    extractor = FakeExtractor()

    build_order_processing_graph(rewrite, extractor).invoke(_state(history, context))

    assert history.to_dict() == history_before
    assert context.to_dict() == context_before


def test_rewrite_error_propagates_and_extractor_is_not_called():
    error = StructuredIntentError("invalid rewrite output")

    class FailingRewrite:
        def rewrite(self, message, history, order_context):
            raise error

    extractor = FakeExtractor()
    with pytest.raises(StructuredIntentError, match="invalid rewrite output"):
        build_order_processing_graph(FailingRewrite(), extractor).invoke(_state())
    assert extractor.calls == []


def test_extract_error_propagates_after_rewrite():
    rewrite = FakeRewriteModel(RewriteResult("本轮新增一吨苹果", "再加一吨苹果"))
    extractor = FakeExtractor(error=StructuredIntentError("invalid extraction output"))

    with pytest.raises(StructuredIntentError, match="invalid extraction output"):
        build_order_processing_graph(rewrite, extractor).invoke(_state())

    assert len(extractor.calls) == 1


def test_graph_applies_entities_to_new_order_context_without_mutating_input():
    original = OrderContext(cargo=[{"name": "苹果", "weight": "1吨"}])
    rewrite = FakeRewriteModel(RewriteResult("再加一吨香蕉", "再加一吨香蕉"))
    extractor = FakeExtractor(
        [Entity("cargo", "add", {"name": "香蕉", "weight": "1吨"}, "一吨香蕉")]
    )

    result = build_order_processing_graph(rewrite, extractor).invoke(_state(context=original))

    assert result["order_context"].cargo == [
        {
            "name": "苹果",
            "weight": ["1吨"],
            "quantity": [],
            "volume": [],
            "dimensions": [],
        },
        {
            "name": "香蕉",
            "weight": ["1吨"],
            "quantity": [],
            "volume": [],
            "dimensions": [],
        },
    ]
    assert result["order_context_updated"] is True
    assert original.cargo == [{"name": "苹果", "weight": "1吨"}]


def test_graph_rebuilds_profile_after_raw_cargo_change_and_keeps_input_pure():
    original = OrderContext()
    rewrite = FakeRewriteModel(RewriteResult("新增一吨香蕉", "新增一吨香蕉"))
    extractor = FakeExtractor([Entity("cargo", "set", {"name": "香蕉", "weight": "1吨"}, "一吨香蕉")])
    profile = FakeCargoProfile(_cargo_profile_result())

    result = build_order_processing_graph(rewrite, extractor, profile).invoke(_state(context=original))

    assert profile.calls == [[{"name": "香蕉", "weight": ["1吨"], "quantity": [], "volume": [], "dimensions": []}]]
    assert result["order_context"].cargo_profiles[0]["name"] == "香蕉"
    assert result["cargo_profile_updated"] is True
    assert original.cargo == []


def test_graph_skips_profile_when_context_update_does_not_change_cargo():
    rewrite = FakeRewriteModel(RewriteResult("设置起运地上海", "设置起运地上海"))
    extractor = FakeExtractor([Entity("location", "set", {"role": "pickup", "city": "上海"}, "上海")])
    profile = FakeCargoProfile(_cargo_profile_result())

    result = build_order_processing_graph(rewrite, extractor, profile).invoke(_state())

    assert profile.calls == []


def test_completeness_node_runs_after_vehicle_resolution_and_returns_summary():
    rewrite = FakeRewriteModel(RewriteResult("设置完整订单", "设置完整订单"))
    extractor = FakeExtractor([])
    context = OrderContext(
        pickup_location={"city": "温州"},
        dropoff_location={"city": "上海"},
        cargo=[{"name": "苹果", "weight": ["1吨"], "quantity": [], "volume": [], "dimensions": []}],
        delivery_time={"start": "2026-08-28T10:00:00"},
    )
    result = build_order_processing_graph(rewrite, extractor).invoke(_state(context=context))
    assert result["order_summary"].status == "complete"
    assert "温州" in result["order_summary"].summary
    assert result["cargo_profile_updated"] is False


def test_profile_error_keeps_original_raw_context_unmodified():
    original = OrderContext(cargo=[{"name": "苹果", "weight": ["1吨"], "quantity": [], "volume": [], "dimensions": []}])
    rewrite = FakeRewriteModel(RewriteResult("再加一吨香蕉", "再加一吨香蕉"))
    extractor = FakeExtractor([Entity("cargo", "add", {"name": "香蕉", "weight": "1吨"}, "一吨香蕉")])
    profile = FakeCargoProfile(error=StructuredIntentError("invalid profile"))

    with pytest.raises(StructuredIntentError, match="invalid profile"):
        build_order_processing_graph(rewrite, extractor, profile).invoke(_state(context=original))
    assert original.cargo == [{"name": "苹果", "weight": ["1吨"], "quantity": [], "volume": [], "dimensions": []}]


def test_graph_repeated_cargo_additions_preserve_raw_expressions():
    rewrite = FakeRewriteModel(RewriteResult("本轮新增货物", "本轮新增货物"))
    extractor = FakeExtractor([
        Entity("cargo", "add", {"name": "香蕉", "weight": "500公斤"}, "500公斤香蕉")
    ])
    graph = build_order_processing_graph(rewrite, extractor)

    first = graph.invoke(_state(context=OrderContext(cargo=[{
        "name": "香蕉",
        "weight": ["1吨"],
        "quantity": [],
        "volume": [],
        "dimensions": [],
    }])))
    second = graph.invoke(_state(context=first["order_context"]))

    assert second["order_context"].cargo == [{
        "name": "香蕉",
        "weight": ["1吨", "500公斤", "500公斤"],
        "quantity": [],
        "volume": [],
        "dimensions": [],
    }]


def test_graph_supports_set_replace_and_remove_context_actions():
    reducer = OrderContextReducer()
    context = OrderContext()
    context = reducer.apply(context, [Entity("location", "set", {"role": "pickup", "city": "上海"})])
    context = reducer.apply(context, [Entity("location", "replace", {"role": "pickup", "city": "杭州"})])
    context = reducer.apply(context, [Entity("vehicle_specs", "set", {"extraction_text": "高顶"})])
    context = reducer.apply(context, [Entity("vehicle_specs", "remove", {"extraction_text": "高顶"})])
    context = reducer.apply(context, [Entity("location", "remove", {"role": "pickup"})])
    assert context.pickup_location is None
    assert context.vehicle_specs == []


def test_unresolved_vehicle_source_is_not_written_as_canonical_context_value():
    context = OrderContext()
    context = OrderContextReducer().apply(
        context,
        [Entity("vehicle_type", "set", {"value": "小车"}, "小车")],
    )
    assert context.vehicle_type is None


def test_resolved_catalog_vehicle_value_can_update_context():
    context = OrderContextReducer().apply(
        OrderContext(),
        [Entity("vehicle_type", "set", {"value": "truck_4m2"}, "4米2")],
    )
    assert context.vehicle_type == "truck_4m2"


def test_vehicle_alias_is_canonicalized_only_at_context_boundary():
    context = OrderContextReducer().apply(
        OrderContext(),
        [Entity("vehicle_type", "set", {"value": "4米2"}, "4米2"), Entity("vehicle_specs", "set", {"value": "冷链"}, "冷链")],
    )
    assert context.vehicle_type == "truck_4m2"
    assert context.vehicle_specs == ["cold_chain"]


def test_best_effort_rewrite_preserves_original_order_context_when_no_entities():
    original = OrderContext(cargo=[{"name": "苹果", "weight": "1吨"}])
    rewrite = FakeRewriteModel(RewriteResult("选择最合理车型", "设置车型"))
    result = build_order_processing_graph(rewrite, FakeExtractor()).invoke(_state(context=original))
    assert result["order_context"] == original
    assert result["order_context_updated"] is False


def test_reducer_failure_does_not_return_partial_context():
    rewrite = FakeRewriteModel(RewriteResult("设置未知字段", "设置未知字段"))
    extractor = FakeExtractor([Entity("unsupported", "set", {"value": "x"}, "未知")])
    with pytest.raises(ContextReductionError):
        build_order_processing_graph(rewrite, extractor).invoke(_state())
