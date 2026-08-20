"""LLM resolver for compact cargo constraint profiles."""

import copy
import json
from numbers import Real
from typing import Any, Mapping, Sequence

from ..infrastructure.llm import ChatMessage, LLMClient
from ..intent.resolver import StructuredIntentError
from .models import CargoProfile, CargoProfileResult, CargoProfileSummary


CARGO_PROFILE_SYSTEM_PROMPT = r"""你是物流订单的货物约束画像生成器。输入是当前订单的完整【原始货物列表】。

请为每种货物生成一个简洁画像，并生成全部货物的汇总。画像只描述货物约束，不做车型推荐、车型筛选、车辆 code 映射或装箱结论。

规则：
1. 核心数值是本次运输货物的总规模：weight_kg（公斤）、volume_m3（立方米）、dimensions_cm（整体占用长宽高，厘米）。
2. 货物类型与重量、数量、包装、体积或尺寸中的任意一项运输规模信息同时存在时，必须强制进行物流常识估算，必须尽力估算核心数值；不能因为用户没有明确给出全部数值就直接返回 null。先尝试沿“货物类型 → 常见单件参数或密度 → 数量/包装 → 堆积密度 → 装车占用体积和整体尺寸”的链路推理。
3. 例如“一吨苹果”必须根据苹果常见单果重量估算数量，再按纸箱或周转筐包装、堆积密度和装车方式估算总体积与整体尺寸；“100箱苹果”必须根据常见箱规估算总重量、总体积与整体尺寸。估算值不要求精确，但必须是可用于车型初筛的具体数值。
4. 只有现有信息完全不足以确定本次运输规模时，核心数值才允许为 null。例如仅知道“苹果”而不知道数量、重量、包装、体积或尺寸时，可以返回 null。
4. stackability 只能是 full、partial、none、unknown；fragility 只能是 low、medium、high、unknown；temperature 只能是 ambient、cool、refrigerated、frozen、unknown。可以根据货物类型进行常识推断，无法判断时使用 unknown。
5. dimensions_cm 表示预计整体装车占用的长宽高，不是单件尺寸。每条画像必须有非空 reason，说明明确值、推导值、常识估算值及主要假设；不得只写“用户未提供”。只有确实没有运输规模时，才说明无法估算的具体原因。不要输出 source、warnings、raw、unit、basis、confidence、assumptions 等字段。
6. 汇总只返回 total_weight_kg、total_volume_m3 和 reason。如果任一货物的对应核心数值在尝试上述推理链后仍完全无法估算，对应汇总值才可以为 null，并在 reason 中说明。
7. 不要将旧画像作为输入或累加来源；只根据本次完整原始货物列表重新生成全量结果。

输出只能是 JSON 对象，不要 Markdown、解释或额外字段，顶层 schema 固定为：
{
  "cargo_profiles": [{
    "name": "货物名称",
    "weight_kg": null,
    "volume_m3": null,
    "dimensions_cm": {"length": null, "width": null, "height": null},
    "stackability": "full|partial|none|unknown",
    "fragility": "low|medium|high|unknown",
    "temperature": "ambient|cool|refrigerated|frozen|unknown",
    "reason": "解释依据或无法估算原因"
  }],
  "cargo_profile_summary": {
    "total_weight_kg": null,
    "total_volume_m3": null,
    "reason": "解释汇总依据或不完整原因"
  }
}

不得输出 vehicle_type、vehicle_specs、recommended_vehicle、vehicle_code、packing_coordinates、可行车型或任何车辆选择字段。"""

_STACK = {"full", "partial", "none", "unknown"}
_FRAGILITY = {"low", "medium", "high", "unknown"}
_TEMPERATURE = {"ambient", "cool", "refrigerated", "frozen", "unknown"}
_FORBIDDEN = {"vehicle_type", "vehicle_specs", "recommended_vehicle", "vehicle_code", "packing_coordinates", "feasible_vehicles"}


def _object(value: Any, label: str) -> Mapping[str, Any]:
    if not isinstance(value, dict):
        raise StructuredIntentError(f"{label} must be an object")
    forbidden = _FORBIDDEN.intersection(value)
    if forbidden:
        raise StructuredIntentError(f"cargo profile contains forbidden field: {sorted(forbidden)[0]}")
    return value


def _required(value: Mapping[str, Any], fields: Sequence[str], label: str) -> None:
    missing = [field for field in fields if field not in value]
    if missing:
        raise StructuredIntentError(f"{label} missing field: {missing[0]}")


def _only_fields(value: Mapping[str, Any], fields: Sequence[str], label: str) -> None:
    extra = set(value).difference(fields)
    if extra:
        raise StructuredIntentError(f"{label} has unexpected field: {sorted(extra)[0]}")


def _number_or_none(value: Any, label: str) -> None:
    if value is not None and (not isinstance(value, Real) or isinstance(value, bool)):
        raise StructuredIntentError(f"{label} must be a number or null")
    if isinstance(value, Real) and value < 0:
        raise StructuredIntentError(f"{label} must not be negative")


def _reason(value: Any, label: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise StructuredIntentError(f"{label} must be a non-empty string")


def parse_cargo_profile_result(value: Mapping[str, Any]) -> CargoProfileResult:
    root = _object(value, "profile output")
    _required(root, ("cargo_profiles", "cargo_profile_summary"), "profile output")
    _only_fields(root, ("cargo_profiles", "cargo_profile_summary"), "profile output")
    profiles = root["cargo_profiles"]
    if not isinstance(profiles, list):
        raise StructuredIntentError("cargo_profiles must be an array")

    parsed = []
    for index, raw in enumerate(profiles):
        item = _object(raw, f"cargo_profiles[{index}]")
        fields = ("name", "weight_kg", "volume_m3", "dimensions_cm", "stackability", "fragility", "temperature", "reason")
        _required(item, fields, f"cargo_profiles[{index}]")
        _only_fields(item, fields, f"cargo_profiles[{index}]")
        if not isinstance(item["name"], str) or not item["name"].strip():
            raise StructuredIntentError(f"cargo_profiles[{index}].name must be a non-empty string")
        _number_or_none(item["weight_kg"], f"cargo_profiles[{index}].weight_kg")
        _number_or_none(item["volume_m3"], f"cargo_profiles[{index}].volume_m3")
        dimensions = _object(item["dimensions_cm"], f"cargo_profiles[{index}].dimensions_cm")
        _required(dimensions, ("length", "width", "height"), f"cargo_profiles[{index}].dimensions_cm")
        _only_fields(dimensions, ("length", "width", "height"), f"cargo_profiles[{index}].dimensions_cm")
        for key in ("length", "width", "height"):
            _number_or_none(dimensions[key], f"cargo_profiles[{index}].dimensions_cm.{key}")
        if item["stackability"] not in _STACK:
            raise StructuredIntentError(f"cargo_profiles[{index}].stackability is invalid")
        if item["fragility"] not in _FRAGILITY:
            raise StructuredIntentError(f"cargo_profiles[{index}].fragility is invalid")
        if item["temperature"] not in _TEMPERATURE:
            raise StructuredIntentError(f"cargo_profiles[{index}].temperature is invalid")
        _reason(item["reason"], f"cargo_profiles[{index}].reason")
        parsed.append(CargoProfile(**{key: copy.deepcopy(item[key]) for key in fields}))

    summary = _object(root["cargo_profile_summary"], "cargo_profile_summary")
    fields = ("total_weight_kg", "total_volume_m3", "reason")
    _required(summary, fields, "cargo_profile_summary")
    _only_fields(summary, fields, "cargo_profile_summary")
    _number_or_none(summary["total_weight_kg"], "summary.total_weight_kg")
    _number_or_none(summary["total_volume_m3"], "summary.total_volume_m3")
    _reason(summary["reason"], "summary.reason")
    return CargoProfileResult(parsed, CargoProfileSummary(**{key: copy.deepcopy(summary[key]) for key in fields}))


def parse_cargo_profile_from_text(text: str) -> CargoProfileResult:
    try:
        value = json.loads(text)
    except (TypeError, ValueError) as exc:
        raise StructuredIntentError("LLM returned invalid cargo profile JSON") from exc
    if not isinstance(value, dict):
        raise StructuredIntentError("LLM cargo profile output must be a JSON object")
    return parse_cargo_profile_result(value)


def _validate_against_raw_cargo(result: CargoProfileResult, cargo: Sequence[Mapping[str, Any]]) -> None:
    expected = {str(item.get("name")) for item in cargo}
    actual = {profile.name for profile in result.cargo_profiles}
    if actual != expected:
        raise StructuredIntentError("cargo profiles must correspond exactly to the raw cargo names")


class CargoProfileResolver:
    def __init__(self, client: LLMClient):
        self.client = client

    def profile(self, cargo: Sequence[Mapping[str, Any]]) -> CargoProfileResult:
        snapshot = copy.deepcopy([dict(item) for item in cargo])
        message = "【原始货物列表】\n" + json.dumps(snapshot, ensure_ascii=False, indent=2)
        response = self.client.chat([ChatMessage("system", CARGO_PROFILE_SYSTEM_PROMPT), ChatMessage("user", message)])
        result = parse_cargo_profile_from_text(response.text)
        _validate_against_raw_cargo(result, snapshot)
        return result


__all__ = ["CARGO_PROFILE_SYSTEM_PROMPT", "CargoProfileResolver", "parse_cargo_profile_result", "parse_cargo_profile_from_text"]
