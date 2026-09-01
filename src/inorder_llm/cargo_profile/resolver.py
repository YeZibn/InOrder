"""LLM resolver for compact cargo constraint profiles."""

import copy
import json
from numbers import Real
from typing import Any, Mapping, Sequence

from ..infrastructure.llm import ChatMessage, LLMClient
from ..infrastructure.llm.text import strip_json_prefix
from ..infrastructure.llm.structured import call_with_format_repair
from ..intent.resolver import StructuredIntentError
from .models import CargoProfile, CargoProfileResult, CargoProfileSummary


CARGO_PROFILE_SYSTEM_PROMPT = r"""你是物流订单的货物约束画像生成器。输入是当前订单的完整【原始货物列表】。

请为每种货物生成一个简洁画像，并生成全部货物的汇总。画像只描述货物约束，不做车型推荐、车型筛选、车辆 code 映射或装箱结论。

规则：
1. 核心数值是本次运输货物的总规模：weight_kg（公斤）、volume_m3（立方米）、dimensions_cm（整体占用长宽高，厘米）。
2. 货物类型与重量、数量、包装、体积或尺寸中的任意一项运输规模信息同时存在时，必须强制进行物流常识估算，必须尽力估算核心数值；不能因为用户没有明确给出全部数值就直接返回 null。先尝试沿“货物类型 → 常见单件参数或密度 → 数量/包装 → 堆积密度 → 装车占用体积和整体尺寸”的链路推理。
3. 原始货物中同一字段的数组是多轮新增或多条明细，表示累加项，不是候选值、替代值，也不能只取最后一项。必须逐项解析并换算后求和。例如 `weight=["1吨", "1吨"]` 必须得到总重量 `2000kg`；`weight=["1吨", "500公斤"]` 必须得到 `1500kg`。数量、体积数组同样遵循累加规则；尺寸数组按多条货物明细综合估算整体占用尺寸。
4. 例如“一吨苹果”必须根据苹果常见单果重量估算数量，再按纸箱或周转筐包装、堆积密度和装车方式估算总体积与整体尺寸；“100箱苹果”必须根据常见箱规估算总重量、总体积与整体尺寸。估算值不要求精确，但必须是可用于车型初筛的具体数值。
5. 只有现有信息完全不足以确定本次运输规模时，核心数值才允许为 null。例如仅知道“苹果”而不知道数量、重量、包装、体积或尺寸时，可以返回 null。
6. stackability 只能是 full、partial、none、unknown；fragility 只能是 low、medium、high、unknown；temperature 只能是 ambient、cool、refrigerated、frozen、unknown。可以根据货物类型进行常识推断，无法判断时使用 unknown。
7. dimensions_cm 表示预计整体装车占用的长宽高，不是单件尺寸。每条画像必须有非空 reason，说明明确值、推导值、常识估算值及主要假设；不得只写“用户未提供”。只有确实没有运输规模时，才说明无法估算的具体原因。不要输出 source、warnings、raw、unit、basis、confidence、assumptions 等字段。
8. 汇总只返回 total_weight_kg、total_volume_m3 和 reason。如果任一货物的对应核心数值在尝试上述推理链后仍完全无法估算，对应汇总值才可以为 null，并在 reason 中说明；否则汇总必须等于所有画像值之和。
9. 不要将旧画像作为输入或累加来源；只根据本次完整原始货物列表重新生成全量结果。

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


def _explicit_total(values: Any, kind: str) -> float | None:
    """Parse only unambiguous raw additive values for lower-bound checks."""
    import re
    items = values if isinstance(values, (list, tuple)) else [values]
    total = 0.0
    matched = False
    patterns = {
        "weight": [(r"([0-9]+(?:\.[0-9]+)?)\s*(?:吨|t)", 1000.0),
                   (r"([0-9]+(?:\.[0-9]+)?)\s*(?:公斤|千克|kg)", 1.0),
                   (r"([0-9]+(?:\.[0-9]+)?)\s*(?:克|g)", 0.001)],
        "volume": [(r"([0-9]+(?:\.[0-9]+)?)\s*(?:立方米|方|m3)", 1.0),
                    (r"([0-9]+(?:\.[0-9]+)?)\s*(?:立方厘米|cm3)", 1e-6)],
    }
    for item in items:
        if not isinstance(item, str):
            continue
        for pattern, factor in patterns.get(kind, []):
            match = re.fullmatch(r"\s*" + pattern + r"\s*", item, re.I)
            if match:
                total += float(match.group(1)) * factor
                matched = True
                break
    return total if matched else None


def _validate_aggregation(result: CargoProfileResult, cargo: Sequence[Mapping[str, Any]]) -> None:
    """Ensure derived output cannot silently undercount explicit raw details."""
    tolerance = 1e-6
    profiles = {profile.name: profile for profile in result.cargo_profiles}
    if len(profiles) != len(result.cargo_profiles):
        raise StructuredIntentError("cargo profiles must contain one profile per cargo name")
    weight_sum = sum(profile.weight_kg for profile in result.cargo_profiles if profile.weight_kg is not None)
    volume_sum = sum(profile.volume_m3 for profile in result.cargo_profiles if profile.volume_m3 is not None)
    summary = result.cargo_profile_summary
    if summary.total_weight_kg is not None and abs(summary.total_weight_kg - weight_sum) > tolerance:
        raise StructuredIntentError("cargo profile total_weight_kg must equal profile weights")
    if summary.total_volume_m3 is not None and abs(summary.total_volume_m3 - volume_sum) > tolerance:
        raise StructuredIntentError("cargo profile total_volume_m3 must equal profile volumes")
    for raw in cargo:
        name = str(raw.get("name"))
        profile = profiles.get(name)
        if profile is None:
            continue
        explicit_weight = _explicit_total(raw.get("weight"), "weight")
        if explicit_weight is not None and (profile.weight_kg is None or profile.weight_kg + tolerance < explicit_weight):
            raise StructuredIntentError(f"cargo profile weight undercounts raw details for {name}")
        explicit_volume = _explicit_total(raw.get("volume"), "volume")
        if explicit_volume is not None and (profile.volume_m3 is None or profile.volume_m3 + tolerance < explicit_volume):
            raise StructuredIntentError(f"cargo profile volume undercounts raw details for {name}")


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
        value = json.loads(strip_json_prefix(text))
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
        messages = [ChatMessage("system", CARGO_PROFILE_SYSTEM_PROMPT), ChatMessage("user", message)]
        def parse_and_validate(text: str) -> CargoProfileResult:
            result = parse_cargo_profile_from_text(text)
            _validate_against_raw_cargo(result, snapshot)
            _validate_aggregation(result, snapshot)
            return result

        result = call_with_format_repair(
            self.client,
            messages,
            parse_and_validate,
            "上一次输出未正确按原始明细累加或汇总不一致。请重新计算所有数组明细，严格只返回约定的货物画像 JSON，不要添加解释或 Markdown。",
        )
        return result


__all__ = ["CARGO_PROFILE_SYSTEM_PROMPT", "CargoProfileResolver", "parse_cargo_profile_result", "parse_cargo_profile_from_text"]
