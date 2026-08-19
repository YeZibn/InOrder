"""Strict LLM resolver for cargo constraint profiles."""

import copy
import json
from numbers import Real
from typing import Any, Mapping, Sequence

from ..infrastructure.llm import ChatMessage, LLMClient
from ..intent.resolver import StructuredIntentError
from .models import CargoProfile, CargoProfileResult, CargoProfileSummary


CARGO_PROFILE_SYSTEM_PROMPT = r"""你是物流订单的货物约束画像生成器。你的输入是当前订单的完整【原始货物列表】，每条记录中的字符串都代表用户明确表达的原始事实。

你的任务是为列表中的每种货物生成一条画像，并生成当前货物集合的汇总。画像只描述货物约束，不做车型推荐、车型筛选、车辆 code 映射、装箱坐标或装箱结论。

必须遵守：
1. 原始 cargo 是唯一事实来源；不要修改、规范化、翻译或覆盖原始表达。weight、quantity、volume、dimensions 的 raw 必须回显对应原始字符串列表。
2. 用户明确给出的值标记 basis=explicit；由其他明确字段计算的值标记 basis=derived；基于常见货物知识的推断标记 basis=estimated；无法可靠知道标记 basis=unknown，并使用 null 或 unknown，不得伪造精确数字。
3. 每个估算或推断都要在 assumptions 中说明依据；冲突、重复、无法判断增量还是总量等问题写入 warnings。confidence 只能是 high、medium、low、unknown。
4. quantity、weight、dimensions、volume 均必须保留 basis 和 confidence。stackability、fragility、temperature 也必须保留 basis 和 confidence，并可写 reason。
5. 总体积 total_volume_m3 指预计装车占用体积，不是简单把松散体积当成装车体积。不能可靠汇总时返回 null，并把 volume_status 设为 partial 或 unknown。
6. 不要将旧画像作为输入或累加来源；只根据本次完整原始货物列表重新生成全量结果。

输出只能是 JSON 对象，不要 Markdown、解释或额外字段，顶层 schema 固定为：
{
  "cargo_profiles": [{
    "name": "货物名称",
    "quantity": {"value": null, "unit": "unknown", "raw": [], "basis": "unknown", "confidence": "unknown"},
    "weight": {"total_kg": null, "per_unit_kg": null, "raw": [], "basis": "unknown", "confidence": "unknown"},
    "dimensions": {"length_cm": null, "width_cm": null, "height_cm": null, "scope": "unknown", "shape": "unknown", "raw": [], "basis": "unknown", "confidence": "unknown"},
    "volume": {"unit_m3": null, "total_m3": null, "raw": [], "basis": "unknown", "confidence": "unknown"},
    "stackability": {"value": "full|partial|none|unknown", "basis": "unknown", "confidence": "unknown", "reason": null},
    "fragility": {"value": "low|medium|high|unknown", "basis": "unknown", "confidence": "unknown", "reason": null},
    "temperature": {"requirement": "ambient|cool|refrigerated|frozen|unknown", "basis": "unknown", "confidence": "unknown", "reason": null},
    "assumptions": [], "warnings": []
  }],
  "cargo_profile_summary": {"total_weight_kg": null, "total_volume_m3": null, "weight_status": "explicit|derived|estimated|partial|unknown", "volume_status": "explicit|derived|estimated|partial|unknown", "confidence": "high|medium|low|unknown", "warnings": []}
}

不得输出 vehicle_type、vehicle_specs、recommended_vehicle、vehicle_code、packing_coordinates、可行车型或任何车辆选择字段。"""

_BASIS = {"explicit", "estimated", "derived", "unknown"}
_CONFIDENCE = {"high", "medium", "low", "unknown"}
_STACK = {"full", "partial", "none", "unknown"}
_FRAGILITY = {"low", "medium", "high", "unknown"}
_TEMPERATURE = {"ambient", "cool", "refrigerated", "frozen", "unknown"}
_STATUS = _BASIS | {"partial"}
_FORBIDDEN = {"vehicle_type", "vehicle_specs", "recommended_vehicle", "vehicle_code", "packing_coordinates", "feasible_vehicles"}


def _object(value: Any, label: str) -> Mapping[str, Any]:
    if not isinstance(value, dict):
        raise StructuredIntentError(f"{label} must be an object")
    forbidden = _FORBIDDEN.intersection(value)
    if forbidden:
        raise StructuredIntentError(f"cargo profile contains forbidden field: {sorted(forbidden)[0]}")
    return value


def _required(value: Mapping[str, Any], fields: Sequence[str], label: str) -> None:
    for field in fields:
        if field not in value:
            raise StructuredIntentError(f"{label} missing field: {field}")


def _only_fields(value: Mapping[str, Any], fields: Sequence[str], label: str) -> None:
    extra = set(value).difference(fields)
    if extra:
        raise StructuredIntentError(f"{label} has unexpected field: {sorted(extra)[0]}")


def _number_or_none(value: Any, label: str) -> None:
    if value is not None and (not isinstance(value, Real) or isinstance(value, bool)):
        raise StructuredIntentError(f"{label} must be a number or null")
    if isinstance(value, Real) and value < 0:
        raise StructuredIntentError(f"{label} must not be negative")


def _provenance(value: Mapping[str, Any], label: str) -> None:
    if value.get("basis") not in _BASIS:
        raise StructuredIntentError(f"{label}.basis is invalid")
    if value.get("confidence") not in _CONFIDENCE:
        raise StructuredIntentError(f"{label}.confidence is invalid")


def _list(value: Any, label: str) -> None:
    if not isinstance(value, list):
        raise StructuredIntentError(f"{label} must be an array")


def _string_list(value: Any, label: str) -> None:
    _list(value, label)
    if not all(isinstance(item, str) for item in value):
        raise StructuredIntentError(f"{label} must contain only strings")


def _reason(value: Any, label: str) -> None:
    if value is not None and not isinstance(value, str):
        raise StructuredIntentError(f"{label}.reason must be a string or null")


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
        _required(item, ("name", "quantity", "weight", "dimensions", "volume", "stackability", "fragility", "temperature", "assumptions", "warnings"), f"cargo_profiles[{index}]")
        _only_fields(item, ("name", "quantity", "weight", "dimensions", "volume", "stackability", "fragility", "temperature", "assumptions", "warnings"), f"cargo_profiles[{index}]")
        if not isinstance(item["name"], str) or not item["name"].strip():
            raise StructuredIntentError(f"cargo_profiles[{index}].name must be a non-empty string")
        for key in ("quantity", "weight", "dimensions", "volume", "stackability", "fragility", "temperature"):
            _object(item[key], f"cargo_profiles[{index}].{key}")
        quantity = item["quantity"]
        _required(quantity, ("value", "unit", "raw", "basis", "confidence"), f"cargo_profiles[{index}].quantity")
        _only_fields(quantity, ("value", "unit", "raw", "basis", "confidence"), "quantity")
        _number_or_none(quantity["value"], f"cargo_profiles[{index}].quantity.value")
        if not isinstance(quantity["unit"], str): raise StructuredIntentError("quantity.unit must be a string")
        _list(quantity["raw"], "quantity.raw"); _provenance(quantity, f"cargo_profiles[{index}].quantity")
        weight = item["weight"]
        _required(weight, ("total_kg", "per_unit_kg", "raw", "basis", "confidence"), f"cargo_profiles[{index}].weight")
        _only_fields(weight, ("total_kg", "per_unit_kg", "raw", "basis", "confidence"), "weight")
        _number_or_none(weight["total_kg"], "weight.total_kg"); _number_or_none(weight["per_unit_kg"], "weight.per_unit_kg")
        _list(weight["raw"], "weight.raw"); _provenance(weight, f"cargo_profiles[{index}].weight")
        dimensions = item["dimensions"]
        _required(dimensions, ("length_cm", "width_cm", "height_cm", "scope", "shape", "raw", "basis", "confidence"), f"cargo_profiles[{index}].dimensions")
        _only_fields(dimensions, ("length_cm", "width_cm", "height_cm", "scope", "shape", "raw", "basis", "confidence"), "dimensions")
        for key in ("length_cm", "width_cm", "height_cm"): _number_or_none(dimensions[key], f"dimensions.{key}")
        if not isinstance(dimensions["scope"], str) or not isinstance(dimensions["shape"], str): raise StructuredIntentError("dimensions scope/shape must be strings")
        _list(dimensions["raw"], "dimensions.raw"); _provenance(dimensions, f"cargo_profiles[{index}].dimensions")
        volume = item["volume"]
        _required(volume, ("unit_m3", "total_m3", "raw", "basis", "confidence"), f"cargo_profiles[{index}].volume")
        _only_fields(volume, ("unit_m3", "total_m3", "raw", "basis", "confidence"), "volume")
        _number_or_none(volume["unit_m3"], "volume.unit_m3"); _number_or_none(volume["total_m3"], "volume.total_m3")
        _list(volume["raw"], "volume.raw"); _provenance(volume, f"cargo_profiles[{index}].volume")
        stack = item["stackability"]; _required(stack, ("value", "basis", "confidence", "reason"), "stackability"); _only_fields(stack, ("value", "basis", "confidence", "reason"), "stackability")
        if stack["value"] not in _STACK: raise StructuredIntentError("stackability.value is invalid")
        _provenance(stack, "stackability"); _reason(stack["reason"], "stackability")
        fragility = item["fragility"]; _required(fragility, ("value", "basis", "confidence", "reason"), "fragility"); _only_fields(fragility, ("value", "basis", "confidence", "reason"), "fragility")
        if fragility["value"] not in _FRAGILITY: raise StructuredIntentError("fragility.value is invalid")
        _provenance(fragility, "fragility"); _reason(fragility["reason"], "fragility")
        temperature = item["temperature"]; _required(temperature, ("requirement", "basis", "confidence", "reason"), "temperature"); _only_fields(temperature, ("requirement", "basis", "confidence", "reason"), "temperature")
        if temperature["requirement"] not in _TEMPERATURE: raise StructuredIntentError("temperature.requirement is invalid")
        _provenance(temperature, "temperature"); _reason(temperature["reason"], "temperature")
        _string_list(item["assumptions"], f"cargo_profiles[{index}].assumptions"); _string_list(item["warnings"], f"cargo_profiles[{index}].warnings")
        parsed.append(CargoProfile(**{key: copy.deepcopy(item[key]) for key in ("name", "quantity", "weight", "dimensions", "volume", "stackability", "fragility", "temperature", "assumptions", "warnings")}))

    summary = _object(root["cargo_profile_summary"], "cargo_profile_summary")
    _required(summary, ("total_weight_kg", "total_volume_m3", "weight_status", "volume_status", "confidence", "warnings"), "cargo_profile_summary")
    _only_fields(summary, ("total_weight_kg", "total_volume_m3", "weight_status", "volume_status", "confidence", "warnings"), "cargo_profile_summary")
    _number_or_none(summary["total_weight_kg"], "summary.total_weight_kg"); _number_or_none(summary["total_volume_m3"], "summary.total_volume_m3")
    if summary["weight_status"] not in _STATUS or summary["volume_status"] not in _STATUS: raise StructuredIntentError("summary status is invalid")
    if summary["confidence"] not in _CONFIDENCE: raise StructuredIntentError("summary.confidence is invalid")
    _string_list(summary["warnings"], "summary.warnings")
    return CargoProfileResult(parsed, CargoProfileSummary(**{key: copy.deepcopy(summary[key]) for key in ("total_weight_kg", "total_volume_m3", "weight_status", "volume_status", "confidence", "warnings")}))


def parse_cargo_profile_from_text(text: str) -> CargoProfileResult:
    try:
        value = json.loads(text)
    except (TypeError, ValueError) as exc:
        raise StructuredIntentError("LLM returned invalid cargo profile JSON") from exc
    if not isinstance(value, dict):
        raise StructuredIntentError("LLM cargo profile output must be a JSON object")
    return parse_cargo_profile_result(value)


def _validate_against_raw_cargo(result: CargoProfileResult, cargo: Sequence[Mapping[str, Any]]) -> None:
    """Check only source correspondence, never infer cargo semantics locally."""
    expected = {str(item.get("name")): item for item in cargo}
    actual = {profile.name: profile.to_dict() for profile in result.cargo_profiles}
    if set(actual) != set(expected):
        raise StructuredIntentError("cargo profiles must correspond exactly to the raw cargo names")
    for name, raw in expected.items():
        profile = actual[name]
        for field in ("quantity", "weight", "dimensions", "volume"):
            expected_raw = raw.get(field, [])
            if not isinstance(expected_raw, list):
                expected_raw = [expected_raw]
            if profile[field]["raw"] != expected_raw:
                raise StructuredIntentError(f"cargo profile {name}.{field}.raw must preserve raw cargo expressions")


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
