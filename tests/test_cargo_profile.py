import copy
import json

import pytest

from inorder_llm.cargo_profile import (
    CARGO_PROFILE_SYSTEM_PROMPT,
    CargoProfileResolver,
    parse_cargo_profile_from_text,
    regenerate_cargo_profile,
)
from inorder_llm.context import OrderContext
from inorder_llm.infrastructure.llm import LLMResponse
from inorder_llm.intent.resolver import StructuredIntentError


def _profile(name="香蕉", *, volume=1.8, volume_basis="estimated"):
    return {
        "name": name,
        "quantity": {"value": None, "unit": "unknown", "raw": [], "basis": "unknown", "confidence": "unknown"},
        "weight": {"total_kg": 1000.0, "per_unit_kg": None, "raw": ["1吨"], "basis": "explicit", "confidence": "high"},
        "dimensions": {"length_cm": 100.0, "width_cm": 100.0, "height_cm": 100.0, "scope": "overall", "shape": "unknown", "raw": ["1米×1米×1米"], "basis": "explicit", "confidence": "high"},
        "volume": {"unit_m3": None, "total_m3": volume, "raw": [], "basis": volume_basis, "confidence": "medium" if volume_basis == "estimated" else "high"},
        "stackability": {"value": "partial", "basis": "estimated", "confidence": "medium", "reason": "按常见包装估计"},
        "fragility": {"value": "low", "basis": "estimated", "confidence": "medium", "reason": "按常见货物估计"},
        "temperature": {"requirement": "ambient", "basis": "estimated", "confidence": "medium", "reason": "未说明冷藏"},
        "assumptions": ["使用常见包装估算"],
        "warnings": [],
    }


def _payload(profiles=None, *, volume=1.8, volume_status="estimated"):
    return {
        "cargo_profiles": profiles if profiles is not None else [_profile()],
        "cargo_profile_summary": {
            "total_weight_kg": 1000.0,
            "total_volume_m3": volume,
            "weight_status": "explicit",
            "volume_status": volume_status,
            "confidence": "medium",
            "warnings": [],
        },
    }


class FakeClient:
    def __init__(self, payload):
        self.payload = payload
        self.calls = []

    def chat(self, messages):
        self.calls.append(messages)
        return LLMResponse(json.dumps(self.payload, ensure_ascii=False), "test")


class FakeProfileModel:
    def __init__(self, payload):
        self.payload = payload
        self.calls = []

    def profile(self, cargo):
        self.calls.append(copy.deepcopy(cargo))
        return parse_cargo_profile_from_text(json.dumps(self.payload, ensure_ascii=False))


def test_resolver_profiles_complete_raw_snapshot_without_mutating_it():
    raw = [{"name": "香蕉", "weight": ["1吨"], "quantity": [], "volume": [], "dimensions": ["1米×1米×1米"]}]
    before = copy.deepcopy(raw)
    client = FakeClient(_payload())

    result = CargoProfileResolver(client).profile(raw)

    assert raw == before
    assert result.to_dict()["cargo_profiles"][0]["weight"]["total_kg"] == 1000.0
    system, user = client.calls[0]
    assert system.role == "system" and user.role == "user"
    assert "【原始货物列表】" in user.content
    assert json.loads(user.content.split("\n", 1)[1]) == raw


def test_profile_prompt_requires_provenance_uncertainty_and_no_vehicle_selection():
    assert "basis=explicit" in CARGO_PROFILE_SYSTEM_PROMPT
    assert "assumptions" in CARGO_PROFILE_SYSTEM_PROMPT
    assert "warnings" in CARGO_PROFILE_SYSTEM_PROMPT
    assert "不得输出 vehicle_type" in CARGO_PROFILE_SYSTEM_PROMPT


def test_resolver_rejects_raw_expression_mismatch():
    raw = [{"name": "香蕉", "weight": ["500公斤"], "quantity": [], "volume": [], "dimensions": ["1米×1米×1米"]}]
    with pytest.raises(StructuredIntentError, match="raw"):
        CargoProfileResolver(FakeClient(_payload())).profile(raw)


def test_parse_keeps_explicit_values_raw_expression_and_transport_properties():
    result = parse_cargo_profile_from_text(json.dumps(_payload(), ensure_ascii=False))
    profile = result.to_dict()["cargo_profiles"][0]
    assert profile["weight"] == _profile()["weight"]
    assert profile["dimensions"]["scope"] == "overall"
    assert profile["stackability"]["value"] == "partial"
    assert profile["fragility"]["value"] == "low"
    assert profile["temperature"]["requirement"] == "ambient"


def test_parse_allows_unknown_and_partial_totals_with_assumptions_and_warnings():
    profile = _profile(volume=None, volume_basis="unknown")
    profile["volume"]["confidence"] = "unknown"
    profile["assumptions"] = []
    profile["warnings"] = ["未提供包装规格，无法估算体积"]
    payload = _payload([profile], volume=None, volume_status="partial")
    payload["cargo_profile_summary"]["warnings"] = ["总体积不完整"]

    result = parse_cargo_profile_from_text(json.dumps(payload, ensure_ascii=False)).to_dict()

    assert result["cargo_profiles"][0]["volume"]["total_m3"] is None
    assert result["cargo_profile_summary"]["volume_status"] == "partial"
    assert result["cargo_profile_summary"]["warnings"] == ["总体积不完整"]


@pytest.mark.parametrize(("path", "value"), [
    (("stackability", "value"), "sometimes"),
    (("fragility", "value"), "very_high"),
    (("temperature", "requirement"), "warm"),
])
def test_parse_rejects_invalid_transport_property_enums(path, value):
    payload = _payload()
    payload["cargo_profiles"][0][path[0]][path[1]] = value
    with pytest.raises(StructuredIntentError):
        parse_cargo_profile_from_text(json.dumps(payload, ensure_ascii=False))


def test_parse_rejects_vehicle_selection_fields():
    payload = _payload()
    payload["cargo_profiles"][0]["recommended_vehicle"] = "truck_4m2"
    with pytest.raises(StructuredIntentError, match="forbidden"):
        parse_cargo_profile_from_text(json.dumps(payload, ensure_ascii=False))


def test_regeneration_replaces_old_profiles_after_cargo_mutations_without_double_counting():
    first = _payload()
    second_profile = _profile("苹果", volume=2.0)
    second = _payload([second_profile], volume=2.0)
    model = FakeProfileModel(first)
    original = OrderContext(
        cargo=[{"name": "香蕉", "weight": ["1吨"], "quantity": [], "volume": [], "dimensions": []}],
        cargo_profiles=[{"name": "旧货物"}],
        cargo_profile_summary={"total_weight_kg": 9999},
    )

    updated = regenerate_cargo_profile(original, model)
    assert original.cargo_profiles == [{"name": "旧货物"}]
    assert updated.cargo_profiles[0]["name"] == "香蕉"
    assert model.calls == [original.cargo]

    model.payload = second
    updated.cargo = [{"name": "苹果", "weight": ["1吨"], "quantity": [], "volume": [], "dimensions": []}]
    rebuilt = regenerate_cargo_profile(updated, model)
    assert [item["name"] for item in rebuilt.cargo_profiles] == ["苹果"]
    assert rebuilt.cargo_profile_summary["total_volume_m3"] == 2.0
    assert model.calls[-1] == updated.cargo


def test_empty_cargo_clears_derived_profiles_without_backend_call():
    model = FakeProfileModel(_payload())
    updated = regenerate_cargo_profile(OrderContext(cargo_profiles=[{"name": "旧货物"}], cargo_profile_summary={"x": 1}), model)
    assert updated.cargo_profiles == []
    assert updated.cargo_profile_summary is None
    assert model.calls == []
