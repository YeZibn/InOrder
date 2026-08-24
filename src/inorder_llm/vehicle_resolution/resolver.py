"""Deterministic vehicle estimation and simplified extreme-point fitting."""

from dataclasses import dataclass
from itertools import permutations
from math import prod
from typing import Any, Mapping, Sequence

from ..catalog import VehicleType, get_vehicle_spec, get_vehicle_type, iter_vehicle_types
from ..intent.resolver import StructuredIntentError
from .models import VehicleResolutionResult


@dataclass(frozen=True)
class _Box:
    name: str
    size_cm: tuple[float, float, float]
    volume_m3: float
    weight_kg: float


@dataclass(frozen=True)
class _Placed:
    point: tuple[float, float, float]
    size: tuple[float, float, float]


def _number(value: Any) -> float | None:
    return float(value) if isinstance(value, (int, float)) and value >= 0 else None


def _boxes(profiles: Sequence[Mapping[str, Any]]) -> list[_Box]:
    result = []
    for index, profile in enumerate(profiles):
        dims = profile.get("dimensions_cm") or {}
        values = tuple(_number(dims.get(key)) for key in ("length", "width", "height"))
        if any(value is None or value <= 0 for value in values):
            continue
        volume = _number(profile.get("volume_m3"))
        weight = _number(profile.get("weight_kg"))
        if volume is None:
            volume = prod(values) / 1_000_000
        result.append(_Box(str(profile.get("name") or f"cargo_{index + 1}"), values, volume, weight or 0.0))
    return sorted(result, key=lambda item: (-item.volume_m3, -max(item.size_cm)))


def _overlap(a: _Placed, b: _Placed) -> bool:
    return all(
        a.point[index] < b.point[index] + b.size[index]
        and b.point[index] < a.point[index] + a.size[index]
        for index in range(3)
    )


def _fit(boxes: Sequence[_Box], capacity_cm: tuple[float, float, float]) -> tuple[bool, float]:
    if not boxes:
        return True, 0.0
    points: list[tuple[float, float, float]] = [(0.0, 0.0, 0.0)]
    placed: list[_Placed] = []
    for box in boxes:
        selected = None
        for point in points:
            for size in dict.fromkeys(permutations(box.size_cm)):
                if any(point[i] + size[i] > capacity_cm[i] + 1e-6 for i in range(3)):
                    continue
                candidate = _Placed(point, size)
                if any(_overlap(candidate, other) for other in placed):
                    continue
                selected = candidate
                break
            if selected:
                break
        if selected is None:
            return False, 0.0
        placed.append(selected)
        x, y, z = selected.point
        lx, ly, lz = selected.size
        points.extend(((x + lx, y, z), (x, y + ly, z), (x, y, z + lz)))
        points = list(dict.fromkeys(points))
    used_volume = sum(prod(item.size) for item in placed) / 1_000_000
    return True, used_volume


def _max_range(value: tuple[float, float] | None) -> float:
    return float(value[1]) if value else 0.0


def _required_specs(profiles: Sequence[Mapping[str, Any]]) -> list[str]:
    temperatures = {profile.get("temperature") for profile in profiles}
    return ["cold_chain"] if temperatures.intersection({"refrigerated", "frozen"}) else []


def _candidate(vehicle: VehicleType, specs: list[str], boxes: Sequence[_Box], total_weight: float, total_volume: float) -> Mapping[str, Any] | None:
    payload = _max_range(vehicle.payload_t) * 1000
    volume = _max_range(vehicle.volume_m3)
    capacity = (_max_range(vehicle.length_m) * 100, _max_range(vehicle.width_m) * 100, _max_range(vehicle.height_m) * 100)
    if total_weight > payload + 1e-6 or total_volume > volume + 1e-6:
        return None
    fitted, used = _fit(boxes, capacity)
    if not fitted:
        return None
    return {
        "vehicle_type": vehicle.code,
        "vehicle_specs": list(specs),
        "fit": True,
        "volume_slack_m3": round(max(volume - total_volume, 0.0), 3),
        "payload_slack_kg": round(max(payload - total_weight, 0.0), 1),
        "used_volume_m3": round(used, 3),
        "reason": "通过总重量、总体积和多货物整体箱极点计算。",
    }


class VehicleResolutionResolver:
    """Drop-in replacement for the old LLM resolver; it never calls an LLM."""

    def __init__(self, client: Any = None):
        self.client = client  # retained only for constructor compatibility

    def resolve(self, cargo_profiles: Sequence[Mapping[str, Any]], summary: Mapping[str, Any] | None, raw_vehicle_text: str | None = None) -> VehicleResolutionResult:
        summary = summary or {}
        total_weight = _number(summary.get("total_weight_kg")) or sum(_number(item.get("weight_kg")) or 0.0 for item in cargo_profiles)
        total_volume = _number(summary.get("total_volume_m3")) or sum(_number(item.get("volume_m3")) or 0.0 for item in cargo_profiles)
        boxes = _boxes(cargo_profiles)
        specs = _required_specs(cargo_profiles)
        candidates = []
        for vehicle in iter_vehicle_types():
            item = _candidate(vehicle, specs, boxes, total_weight, total_volume)
            if item is not None:
                candidates.append(item)
        candidates.sort(key=lambda item: (item["volume_slack_m3"], item["payload_slack_kg"], item["vehicle_type"]))
        candidates = candidates[:3]
        reason = "根据车型表上限、货物总重量/总体积和多货物整体箱极点计算。"
        if raw_vehicle_text:
            reason = f"车型表达“{raw_vehicle_text}”无法唯一匹配，{reason}"
        if not candidates:
            reason += "没有车型通过计算。"
        primary = candidates[0] if candidates else {}
        return VehicleResolutionResult(
            primary.get("vehicle_type", ""), list(primary.get("vehicle_specs", specs)), "estimated", reason,
            raw_vehicle_text, candidates,
        )


def parse_vehicle_estimation(value: Mapping[str, Any]) -> VehicleResolutionResult:
    """Compatibility parser for callers/tests that still provide one result."""
    if not isinstance(value, dict):
        raise StructuredIntentError("vehicle estimation output must be an object")
    vehicle_type = value.get("vehicle_type")
    specs = value.get("vehicle_specs", [])
    reason = value.get("reason")
    if not isinstance(vehicle_type, str) or get_vehicle_type(vehicle_type) is None:
        raise StructuredIntentError("vehicle estimation returned unknown vehicle_type")
    if not isinstance(specs, list) or any(not isinstance(item, str) or get_vehicle_spec(item) is None for item in specs):
        raise StructuredIntentError("vehicle estimation returned unknown vehicle_specs")
    if not isinstance(reason, str) or not reason.strip():
        raise StructuredIntentError("vehicle estimation reason must be non-empty")
    return VehicleResolutionResult(vehicle_type, list(specs), "estimated", reason.strip())


VEHICLE_ESTIMATION_SYSTEM_PROMPT = "车型估算已改为基于 vehicles.json 的确定性计算，不调用大模型。"

__all__ = ["VehicleResolutionResolver", "parse_vehicle_estimation", "VEHICLE_ESTIMATION_SYSTEM_PROMPT"]
