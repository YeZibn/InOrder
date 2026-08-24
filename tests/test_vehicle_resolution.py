import json

import pytest

from inorder_llm.catalog import get_vehicle_type
from inorder_llm.infrastructure.llm import LLMResponse
from inorder_llm.intent.resolver import StructuredIntentError
from inorder_llm.vehicle_resolution import (
    VehicleResolutionResolver,
    VehicleResolutionResult,
    parse_vehicle_estimation,
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
