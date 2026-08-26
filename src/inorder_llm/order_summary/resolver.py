"""Rule-based order completeness validation and summary rendering."""

from typing import Any, Iterable, Mapping

from ..context.models import OrderContext
from ..catalog import get_vehicle_type
from .models import MissingOrderField, OrderSummary


def _value(value: Any) -> Any:
    if hasattr(value, "to_dict"):
        return value.to_dict()
    return value


def _text(value: Any) -> str:
    return str(value).strip() if value is not None else ""


def _location_available(value: Any) -> bool:
    value = _value(value)
    if not isinstance(value, Mapping):
        return bool(_text(value))
    return bool(_text(value.get("city")) or _text(value.get("full_address")))


def _cargo_name(item: Mapping[str, Any]) -> str:
    return _text(item.get("name"))


def _has_cargo_measure(item: Mapping[str, Any]) -> bool:
    for key in ("weight", "quantity"):
        value = item.get(key)
        if isinstance(value, (list, tuple)):
            if any(_text(item) for item in value):
                return True
        elif _text(value):
            return True
    return False


def _valid_delivery_time(value: Any) -> bool:
    value = _value(value)
    if not isinstance(value, Mapping):
        return False
    # History-query time is not a delivery requirement for a new order.
    if _text(value.get("context")).lower() == "history":
        return False
    return bool(_text(value.get("start")) or _text(value.get("end")))


def _missing(context: OrderContext) -> list[MissingOrderField]:
    missing: list[MissingOrderField] = []
    if not _location_available(context.pickup_location):
        missing.append(MissingOrderField("pickup_location", "装货地", "请提供装货城市或完整地址"))
    if not _location_available(context.dropoff_location):
        missing.append(MissingOrderField("dropoff_location", "卸货地", "请提供卸货城市或完整地址"))
    cargo = [item for item in context.cargo if isinstance(item, Mapping)]
    has_cargo_name = any(_cargo_name(item) for item in cargo)
    if not has_cargo_name:
        missing.append(MissingOrderField("cargo.name", "货物名称", "请说明需要运输的货物"))
    if not any(_has_cargo_measure(item) for item in cargo):
        missing.append(MissingOrderField("cargo.weight_or_quantity", "货物重量或数量", "重量和数量至少提供一个"))
    if not _valid_delivery_time(context.delivery_time):
        missing.append(MissingOrderField("delivery_time", "送达时间", "请提供明确的送达日期或时间段"))
    return missing


def _first(values: Iterable[Any]) -> Any:
    for value in values:
        if value is not None and _text(value):
            return value
    return None


def _facts(context: OrderContext, vehicle_resolution: Any = None) -> dict[str, Any]:
    pickup = _value(context.pickup_location) or {}
    dropoff = _value(context.dropoff_location) or {}
    vehicle = _value(vehicle_resolution)
    if not vehicle:
        vehicle = {
            "vehicle_type": context.vehicle_type,
            "vehicle_specs": list(context.vehicle_specs),
            "source": context.vehicle_source,
        }
    return {
        "route": {"pickup": pickup, "dropoff": dropoff},
        "cargo": [dict(item) for item in context.cargo],
        "delivery_time": _value(context.delivery_time),
        "vehicle": vehicle,
    }


def _route_text(context: OrderContext) -> str:
    pickup = _value(context.pickup_location) or {}
    dropoff = _value(context.dropoff_location) or {}
    pickup_text = _text(pickup.get("city") or pickup.get("full_address")) if isinstance(pickup, Mapping) else _text(pickup)
    dropoff_text = _text(dropoff.get("city") or dropoff.get("full_address")) if isinstance(dropoff, Mapping) else _text(dropoff)
    if pickup_text and dropoff_text:
        return f"从{pickup_text}发往{dropoff_text}"
    return ""


def _cargo_text(context: OrderContext) -> str:
    names = [_cargo_name(item) for item in context.cargo if isinstance(item, Mapping) and _cargo_name(item)]
    return "、".join(dict.fromkeys(names))


def _cargo_measure_text(context: OrderContext) -> str:
    parts = []
    for item in context.cargo:
        if not isinstance(item, Mapping):
            continue
        name = _cargo_name(item)
        for key, label in (("weight", "重量"), ("quantity", "数量")):
            value = item.get(key)
            values = value if isinstance(value, (list, tuple)) else [value]
            values = [_text(entry) for entry in values if _text(entry)]
            if values:
                parts.append(f"{name or '货物'}的{label}为{'、'.join(values)}")
    return "，".join(parts)


def _delivery_text(context: OrderContext) -> str:
    value = _value(context.delivery_time)
    if not isinstance(value, Mapping):
        return ""
    start, end = _text(value.get("start")), _text(value.get("end"))
    if start and end and start == end:
        return start
    if start and end:
        return f"{start}至{end}"
    return start or end


def build_order_summary(context: OrderContext, vehicle_resolution: Any = None) -> OrderSummary:
    missing_required = _missing(context)
    facts = _facts(context, vehicle_resolution)
    route = _route_text(context)
    cargo = _cargo_text(context)
    pieces = []
    if route:
        pieces.append(route)
    if cargo:
        pieces.append(f"货物为{cargo}")
    measure = _cargo_measure_text(context)
    if measure:
        pieces.append(measure)
    delivery = _delivery_text(context)
    if delivery:
        pieces.append(f"送达时间为{delivery}")
    summary = "已识别" + "，".join(pieces) + "。" if pieces else "已接收您的订单需求。"
    vehicle = _value(vehicle_resolution) or {}
    vehicle_type = vehicle.get("vehicle_type") if isinstance(vehicle, Mapping) else None
    vehicle_type = vehicle_type or context.vehicle_type
    vehicle_label = vehicle_type
    if vehicle_type:
        record = get_vehicle_type(vehicle_type)
        if record is not None:
            vehicle_label = record.label
    if vehicle_type:
        summary = summary.rstrip("。") + f"，车型为{vehicle_label}。"
    if missing_required:
        labels = "、".join(item.label for item in missing_required)
        next_prompt = f"为了继续为您安排，还需要补充{labels}。"
        status = "incomplete"
        examples = []
        if any(item.field == "delivery_time" for item in missing_required):
            examples.append("例如“明天下午”或“8月28日10点”")
        if any(item.field in ("pickup_location", "dropoff_location") for item in missing_required):
            examples.append("地址可以填写到城市或具体仓库")
        if examples:
            next_prompt += "".join(examples) + "。"
    else:
        next_prompt = "订单信息已准备好，可以继续下单。"
        status = "complete"
    detail = summary[3:] if summary.startswith("已识别") else summary
    if status == "complete":
        user_message = f"已为您整理好这笔运输需求：{detail}\n{next_prompt}"
    else:
        user_message = f"目前已为您识别出：{detail}\n{next_prompt}"
    return OrderSummary(status, summary, facts, missing_required, [], next_prompt, user_message)


def check_order_completeness(context: OrderContext, vehicle_resolution: Any = None) -> OrderSummary:
    """Build a deterministic summary from the final order context."""

    return build_order_summary(context, vehicle_resolution)


__all__ = ["build_order_summary", "check_order_completeness"]
