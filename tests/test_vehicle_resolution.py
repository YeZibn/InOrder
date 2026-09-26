import json

import pytest

from inorder_llm.catalog import VehicleCatalogSnapshot, VehicleType, get_vehicle_type
from inorder_llm.infrastructure.llm import LLMResponse
from inorder_llm.intent.resolver import StructuredIntentError
from inorder_llm.vehicle_resolution import (
    VehicleResolutionResolver,
    VehicleResolutionResult,
    parse_vehicle_estimation,
)


class _StaticCatalogProvider:
    def __init__(self, vehicles):
        self.snapshot = VehicleCatalogSnapshot(tuple(vehicles), ())

    def get_catalog(self, city=None, fallback=True):
        return self.snapshot


def _vehicle(code, *, length, volume, payload):
    return VehicleType(
        code, code, "truck", (code,),
        length_m=length,
        width_m=(1.0, 1.0),
        height_m=(1.0, 1.0),
        volume_m3=volume,
        payload_t=payload,
    )


def _payload(vehicle_type="truck_4m2", specs=None):
    return {
        "vehicle_type": vehicle_type,
        "vehicle_specs": specs or [],
        "reason": "根据货物总重量和总体积选择最小满足车型。",
    }


class FakeClient:
    def __init__(self, payload):
        self.payload = payload
        self.calls = []

    def chat(self, messages):
        self.calls.append(messages)
        return LLMResponse(json.dumps(self.payload, ensure_ascii=False), "test")


def test_estimation_accepts_only_catalog_code():
    result = parse_vehicle_estimation(_payload())
    assert isinstance(result, VehicleResolutionResult)
    assert result.vehicle_type == "truck_4m2"
    assert result.source == "estimated"
    assert get_vehicle_type(result.vehicle_type) is not None


@pytest.mark.parametrize(
    "payload, message",
    [
        (_payload("4米2"), "unknown vehicle_type"),
        (_payload("truck_4m2", ["冷藏车"]), "unknown vehicle_specs"),
        ({"vehicle_type": "truck_4m2", "vehicle_specs": [], "reason": ""}, "reason"),
    ],
)
def test_estimation_rejects_noncanonical_or_invalid_output(payload, message):
    with pytest.raises(StructuredIntentError, match=message):
        parse_vehicle_estimation(payload)


def test_rule_resolver_ignores_client_and_keeps_unresolved_reason():
    class ExplodingClient:
        def chat(self, messages):
            raise AssertionError("vehicle estimation must not call LLM")
    result = VehicleResolutionResolver(ExplodingClient()).resolve(
        [{"name": "苹果", "weight_kg": 1000}],
        {"total_weight_kg": 1000, "total_volume_m3": 1.8},
        "大车",
    )
    assert result.source == "estimated"
    assert result.raw_vehicle_text == "大车"
    assert "大车" in result.reason


def test_rule_resolver_returns_at_most_three_candidates_for_multiple_boxes():
    resolver = VehicleResolutionResolver()
    result = resolver.resolve(
        [
            {"name": "冰箱", "weight_kg": 80, "volume_m3": 1.0, "dimensions_cm": {"length": 180, "width": 80, "height": 70}},
            {"name": "苹果", "weight_kg": 1000, "volume_m3": 1.8, "dimensions_cm": {"length": 120, "width": 100, "height": 150}},
        ],
        {"total_weight_kg": 1080, "total_volume_m3": 2.8},
    )
    assert result.source == "estimated"
    assert 0 <= len(result.candidates) <= 3
    assert result.vehicle_type == result.candidates[0]["vehicle_type"]


def test_rule_resolver_does_not_call_client():
    class ExplodingClient:
        def chat(self, messages):
            raise AssertionError("vehicle estimation must not call LLM")
    result = VehicleResolutionResolver(ExplodingClient()).resolve(
        [{"name": "苹果", "weight_kg": 1000, "volume_m3": 1.8, "dimensions_cm": {"length": 120, "width": 100, "height": 150}}],
        {"total_weight_kg": 1000, "total_volume_m3": 1.8},
    )
    assert result.candidates


def test_rule_resolver_keeps_user_and_cargo_derived_specs_in_result():
    provider = _StaticCatalogProvider([
        _vehicle("small_cold_truck", length=(1.2, 1.2), volume=(1.2, 1.2), payload=(0.5, 0.5)),
    ])
    result = VehicleResolutionResolver(catalog_provider=provider).resolve(
        [{
            "name": "冷藏货物",
            "weight_kg": 100,
            "volume_m3": 1.0,
            "temperature": "refrigerated",
            "dimensions_cm": {"length": 100, "width": 100, "height": 100},
        }],
        {"total_weight_kg": 100, "total_volume_m3": 1.0},
        vehicle_specs=["tail_lift"],
    )

    assert result.vehicle_specs == ["cold_chain", "tail_lift"]
    assert result.candidates[0]["vehicle_specs"] == ["cold_chain", "tail_lift"]


def test_missing_cargo_dimensions_do_not_pass_as_a_feasible_load():
    result = VehicleResolutionResolver().resolve(
        [{"name": "未知尺寸货物", "weight_kg": 100, "volume_m3": 0.2}],
        {"total_weight_kg": 100, "total_volume_m3": 0.2},
    )

    assert result.candidates == []
    assert result.vehicle_type == ""
    assert "缺少有效长宽高" in result.reason


def test_lower_bound_candidates_rank_before_upper_only_and_smallest_fit_wins():
    provider = _StaticCatalogProvider([
        _vehicle("small_lower", length=(1.1, 1.1), volume=(1.2, 1.2), payload=(0.5, 0.5)),
        _vehicle("large_lower", length=(1.3, 1.3), volume=(1.5, 1.5), payload=(0.8, 0.8)),
        _vehicle("upper_only", length=(0.8, 1.2), volume=(0.5, 1.2), payload=(0.3, 0.8)),
        _vehicle("upper_only_larger", length=(0.8, 1.4), volume=(0.5, 1.4), payload=(0.3, 0.9)),
    ])
    result = VehicleResolutionResolver(catalog_provider=provider).resolve(
        [{"name": "货物", "weight_kg": 400, "volume_m3": 1.0,
          "dimensions_cm": {"length": 100, "width": 100, "height": 100}}],
        {"total_weight_kg": 400, "total_volume_m3": 1.0},
    )

    assert [item["vehicle_type"] for item in result.candidates] == [
        "small_lower", "large_lower", "upper_only",
    ]
    assert [item["fit_level"] for item in result.candidates] == [
        "lower_bound_fit", "lower_bound_fit", "upper_bound_only",
    ]
    assert result.vehicle_type == "small_lower"


def test_upper_only_candidates_rank_by_upper_slack_without_a_primary_vehicle():
    provider = _StaticCatalogProvider([
        _vehicle("upper_larger", length=(0.8, 1.4), volume=(0.5, 1.4), payload=(0.3, 0.9)),
        _vehicle("upper_smaller", length=(0.8, 1.2), volume=(0.5, 1.2), payload=(0.3, 0.8)),
    ])
    result = VehicleResolutionResolver(catalog_provider=provider).resolve(
        [{"name": "货物", "weight_kg": 400, "volume_m3": 1.0,
          "dimensions_cm": {"length": 100, "width": 100, "height": 100}}],
        {"total_weight_kg": 400, "total_volume_m3": 1.0},
    )

    assert [item["vehicle_type"] for item in result.candidates] == ["upper_smaller", "upper_larger"]
    assert all(item["fit_level"] == "upper_bound_only" for item in result.candidates)
    assert result.vehicle_type == ""
