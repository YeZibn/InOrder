"""LLM-backed vehicle estimation with catalog-code validation."""

import copy
import json
from typing import Any, Mapping, Sequence

from ..catalog import get_vehicle_spec, get_vehicle_type, iter_vehicle_specs, iter_vehicle_types
from ..infrastructure.llm import ChatMessage, LLMClient
from ..intent.resolver import StructuredIntentError
from .models import VehicleResolutionError, VehicleResolutionResult


def _catalog_text() -> str:
    types = []
    for item in iter_vehicle_types():
        types.append({"code": item.code, "label": item.label, "aliases": list(item.aliases),
                      "length_m": list(item.length_m or ()), "width_m": list(item.width_m or ()),
                      "height_m": list(item.height_m or ()), "volume_m3": list(item.volume_m3 or ()),
                      "payload_t": list(item.payload_t or ())})
    specs = [{"code": item.code, "label": item.label, "aliases": list(item.aliases)} for item in iter_vehicle_specs()]
    return json.dumps({"vehicle_types": types, "vehicle_specs": specs}, ensure_ascii=False)


VEHICLE_ESTIMATION_SYSTEM_PROMPT = r"""你是运输车型估算器。根据当前完整货物画像和车型主数据，选择一个最合适的基础车型。

规则：
1. 只从提供的 vehicle_types.code 中选择 vehicle_type，禁止创造新 code、输出中文名称代替 code 或返回多个基础车型。
2. 根据 total_weight_kg、total_volume_m3、dimensions_cm 以及每种车型的载重、体积和长宽高范围进行估算；优先选择能够覆盖货物规模的最小合理车型。
3. 如果货物画像包含 refrigerated 或 frozen 温度要求，vehicle_specs 必须包含 cold_chain；否则按货物属性选择必要的规格，无法确定时返回空数组。
4. 这是车型估算，不是用户指定车型能力校验；不要输出 feasible、infeasible、unknown 或任何校验结论。
5. reason 必须说明使用的货物画像和车型能力依据；不得输出额外字段。

输出只能是 JSON：
{"vehicle_type": "catalog code", "vehicle_specs": ["catalog spec code"], "reason": "估算依据"}
"""


def parse_vehicle_estimation(value: Mapping[str, Any]) -> VehicleResolutionResult:
    if not isinstance(value, dict):
        raise StructuredIntentError("vehicle estimation output must be an object")
    required = {"vehicle_type", "vehicle_specs", "reason"}
    missing = required.difference(value)
    if missing:
        raise StructuredIntentError("vehicle estimation output missing field: " + sorted(missing)[0])
    extra = set(value).difference(required)
    if extra:
        raise StructuredIntentError("vehicle estimation output has unexpected field: " + sorted(extra)[0])
    vehicle_type = value["vehicle_type"]
    specs = value["vehicle_specs"]
    reason = value["reason"]
    if not isinstance(vehicle_type, str) or get_vehicle_type(vehicle_type) is None:
        raise StructuredIntentError("vehicle estimation returned unknown vehicle_type")
    if not isinstance(specs, list) or any(not isinstance(item, str) or get_vehicle_spec(item) is None for item in specs):
        raise StructuredIntentError("vehicle estimation returned unknown vehicle_specs")
    if len(set(specs)) != len(specs):
        raise StructuredIntentError("vehicle estimation returned duplicate vehicle_specs")
    if not isinstance(reason, str) or not reason.strip():
        raise StructuredIntentError("vehicle estimation reason must be non-empty")
    return VehicleResolutionResult(vehicle_type, list(specs), "estimated", reason.strip())


class VehicleResolutionResolver:
    def __init__(self, client: LLMClient):
        self.client = client

    def resolve(self, cargo_profiles: Sequence[Mapping[str, Any]], summary: Mapping[str, Any] | None, raw_vehicle_text: str | None = None) -> VehicleResolutionResult:
        user = {"cargo_profiles": copy.deepcopy(list(cargo_profiles)), "cargo_profile_summary": copy.deepcopy(summary), "vehicle_catalog": json.loads(_catalog_text())}
        if raw_vehicle_text:
            user["unresolved_vehicle_expression"] = raw_vehicle_text
        response = self.client.chat([ChatMessage("system", VEHICLE_ESTIMATION_SYSTEM_PROMPT), ChatMessage("user", json.dumps(user, ensure_ascii=False, indent=2))])
        try:
            value = json.loads(response.text)
        except (TypeError, ValueError) as exc:
            raise StructuredIntentError("LLM returned invalid vehicle estimation JSON") from exc
        return parse_vehicle_estimation(value)


__all__ = ["VEHICLE_ESTIMATION_SYSTEM_PROMPT", "VehicleResolutionResolver", "parse_vehicle_estimation"]
