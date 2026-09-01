import copy
import json

import pytest

from inorder_llm.cargo_profile import CargoProfileResolver, parse_cargo_profile_from_text
from inorder_llm.context import OrderContext
from inorder_llm.infrastructure.llm import LLMResponse
from inorder_llm.intent.resolver import StructuredIntentError
from inorder_llm.cargo_profile.updater import regenerate_cargo_profile


def _profile(name="香蕉", *, weight=1000.0, volume=1.8):
    return {"name": name, "weight_kg": weight, "volume_m3": volume,
            "dimensions_cm": {"length": 120.0, "width": 100.0, "height": 150.0},
            "stackability": "partial", "fragility": "low", "temperature": "cool",
            "reason": "重量由用户提供，体积和尺寸按常见包装估算。"}


def _payload(profiles=None, *, weight=1000.0, volume=1.8, reason="根据各货物画像汇总。"):
    return {"cargo_profiles": profiles or [_profile()],
            "cargo_profile_summary": {"total_weight_kg": weight, "total_volume_m3": volume, "reason": reason}}


class FakeClient:
    def __init__(self, payload): self.payload, self.calls = payload, []
    def chat(self, messages):
        self.calls.append(messages)
        return LLMResponse(json.dumps(self.payload, ensure_ascii=False), "test")


class FakeProfileModel:
    def __init__(self, payload): self.payload, self.calls = payload, []
    def profile(self, cargo):
        self.calls.append(copy.deepcopy(cargo))
        return parse_cargo_profile_from_text(json.dumps(self.payload, ensure_ascii=False))


def test_resolver_preserves_raw_snapshot_without_mutating_it():
    raw = [{"name": "香蕉", "weight": ["1吨"], "quantity": [], "volume": [], "dimensions": ["1米×1米×1米"]}]
    before = copy.deepcopy(raw)
    client = FakeClient(_payload())
    result = CargoProfileResolver(client).profile(raw)
    assert raw == before
    assert result.to_dict()["cargo_profiles"][0]["weight_kg"] == 1000.0
    assert "【原始货物列表】" in client.calls[0][1].content


def test_prompt_requires_estimation_reason_and_no_legacy_metadata():
    from inorder_llm.cargo_profile import CARGO_PROFILE_SYSTEM_PROMPT
    assert "必须尽力估算" in CARGO_PROFILE_SYSTEM_PROMPT
    assert "reason" in CARGO_PROFILE_SYSTEM_PROMPT
    assert "不得输出 vehicle_type" in CARGO_PROFILE_SYSTEM_PROMPT
    assert "一吨苹果" in CARGO_PROFILE_SYSTEM_PROMPT
    assert "100箱苹果" in CARGO_PROFILE_SYSTEM_PROMPT
    assert "整体装车占用" in CARGO_PROFILE_SYSTEM_PROMPT


def test_one_ton_apples_fixture_requires_estimated_space_values():
    profile = _profile("苹果", weight=1000.0, volume=1.8)
    profile["reason"] = "总重量为用户明确提供的一吨；按苹果常见单果重量估算数量，再按纸箱或周转筐包装和堆积密度估算装车体积与整体尺寸。"
    result = parse_cargo_profile_from_text(json.dumps(_payload([profile]), ensure_ascii=False)).to_dict()
    cargo = result["cargo_profiles"][0]
    assert cargo["weight_kg"] == 1000.0
    assert cargo["volume_m3"] is not None
    assert all(cargo["dimensions_cm"][key] is not None for key in ("length", "width", "height"))


def test_one_hundred_boxes_apples_fixture_estimates_weight_and_space():
    profile = _profile("苹果", weight=2500.0, volume=4.5)
    profile["reason"] = "按常见苹果箱规和单箱重量估算一百箱总重，再根据箱体尺寸、堆叠方式和装车布局估算总体积与整体尺寸。"
    result = parse_cargo_profile_from_text(json.dumps(_payload([profile], weight=2500.0, volume=4.5), ensure_ascii=False)).to_dict()
    assert result["cargo_profiles"][0]["weight_kg"] == 2500.0
    assert result["cargo_profiles"][0]["volume_m3"] == 4.5


def test_parse_compact_profile():
    result = parse_cargo_profile_from_text(json.dumps(_payload(), ensure_ascii=False)).to_dict()
    assert result["cargo_profiles"][0]["dimensions_cm"]["length"] == 120.0
    assert result["cargo_profile_summary"]["total_volume_m3"] == 1.8


def test_parse_allows_null_only_with_reason():
    profile = _profile(weight=None, volume=None)
    profile["dimensions_cm"] = {"length": None, "width": None, "height": None}
    profile["reason"] = "仅提供货物名称，无法估算运输规模。"
    result = parse_cargo_profile_from_text(json.dumps(_payload([profile], weight=None, volume=None), ensure_ascii=False)).to_dict()
    assert result["cargo_profiles"][0]["weight_kg"] is None


def test_parse_rejects_empty_reason():
    payload = _payload(); payload["cargo_profiles"][0]["reason"] = ""
    with pytest.raises(StructuredIntentError, match="reason"):
        parse_cargo_profile_from_text(json.dumps(payload, ensure_ascii=False))


def test_regeneration_replaces_old_profiles_atomically():
    model = FakeProfileModel(_payload())
    original = OrderContext(cargo=[{"name": "香蕉", "weight": ["1吨"], "quantity": [], "volume": [], "dimensions": []}], cargo_profiles=[{"name": "旧货物"}])
    updated = regenerate_cargo_profile(original, model)
    assert original.cargo_profiles == [{"name": "旧货物"}]
    assert updated.cargo_profiles[0]["name"] == "香蕉"
    assert model.calls == [original.cargo]


def test_empty_cargo_clears_profiles_without_backend_call():
    model = FakeProfileModel(_payload())
    updated = regenerate_cargo_profile(OrderContext(cargo_profiles=[{"name": "旧货物"}], cargo_profile_summary={"x": 1}), model)
    assert updated.cargo_profiles == [] and updated.cargo_profile_summary is None
    assert model.calls == []


def test_resolver_rejects_undercounted_repeated_raw_weight_and_repairs():
    raw = [{"name": "苹果", "weight": ["1吨", "1吨"], "quantity": [], "volume": [], "dimensions": []}]
    undercounted = _payload([_profile("苹果", weight=1000.0)], weight=1000.0)
    corrected = _payload([_profile("苹果", weight=2000.0)], weight=2000.0)
    client = FakeClient(undercounted)
    client.payloads = [undercounted, corrected]
    def chat(messages):
        client.calls.append(messages)
        payload = client.payloads.pop(0)
        return LLMResponse(json.dumps(payload, ensure_ascii=False), "test")
    client.chat = chat
    result = CargoProfileResolver(client).profile(raw)
    assert result.cargo_profile_summary.total_weight_kg == 2000.0
    assert len(client.calls) == 2


def test_resolver_requires_profile_summary_to_equal_profile_sum():
    raw = [{"name": "苹果", "weight": ["1吨"], "quantity": [], "volume": [], "dimensions": []}]
    first = _payload([_profile("苹果", weight=1000.0, volume=1.8)], weight=999.0, volume=1.8)
    second = _payload([_profile("苹果", weight=1000.0, volume=1.8)], weight=1000.0, volume=1.8)
    client = FakeClient(first)
    client.payloads = [first, second]
    def chat(messages):
        client.calls.append(messages)
        return LLMResponse(json.dumps(client.payloads.pop(0), ensure_ascii=False), "test")
    client.chat = chat
    result = CargoProfileResolver(client).profile(raw)
    assert result.cargo_profile_summary.total_weight_kg == 1000.0
