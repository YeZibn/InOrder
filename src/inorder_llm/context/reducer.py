"""Apply extracted entity actions to an active order context."""

from copy import deepcopy
import re
from typing import Any, Dict, Iterable, Mapping, Optional

from ..extract.models import Entity
from ..normalization import normalize_entities
from .models import OrderContext


class ContextReductionError(ValueError):
    pass


_SCALAR_TYPES = {
    "vehicle_type": "vehicle_type",
    "follow_car_number": "follow_car_number",
    "oneself_follow_flag": "oneself_follow_flag",
    "invoice_type": "invoice_type",
    "payment_type": "payment_type",
    "service_type": "service_type",
    "order_id": "referenced_order_id",
}


def _value(entity: Entity) -> Any:
    attrs = entity.attributes
    if "value" in attrs:
        return attrs["value"]
    return attrs.get("extraction_text") or entity.extraction_text


def _number(value: Any) -> Optional[float]:
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return float(value)
    if not isinstance(value, str):
        return None
    match = re.search(r"[-+]?\d+(?:\.\d+)?", value)
    return float(match.group()) if match else None


def _add_measure(old: Any, new: Any) -> Any:
    old_num, new_num = _number(old), _number(new)
    if old_num is None or new_num is None:
        raise ContextReductionError("cannot safely add non-numeric cargo measure")
    total = old_num + new_num
    if isinstance(old, int) and isinstance(new, int):
        return int(total)
    if isinstance(old, str):
        match = re.search(r"[-+]?\d+(?:\.\d+)?\s*(.*)$", old)
        suffix = match.group(1) if match else ""
        return (str(int(total)) if total.is_integer() else str(total)) + suffix
    return int(total) if total.is_integer() else total


class OrderContextReducer:
    """Pure reducer: returns a copied context and never calls external services."""

    def apply(self, context: OrderContext, entities: Iterable[Entity]) -> OrderContext:
        result = deepcopy(context)
        for entity in normalize_entities(entities):
            self._apply_one(result, entity)
        return result

    def _apply_one(self, context: OrderContext, entity: Entity) -> None:
        if entity.type == "location":
            self._location(context, entity)
        elif entity.type == "person":
            self._person(context, entity)
        elif entity.type == "phone":
            self._phone(context, entity)
        elif entity.type == "time":
            if entity.attributes.get("context") == "history":
                raise ContextReductionError("history time cannot update delivery_time")
            self._single(context, "delivery_time", dict(entity.attributes), entity)
        elif entity.type == "cargo":
            self._cargo(context, entity)
        elif entity.type == "vehicle_specs":
            self._list(context, "vehicle_specs", _value(entity), entity)
        elif entity.type == "remark":
            self._remark(context, entity)
        elif entity.type in _SCALAR_TYPES:
            self._single(context, _SCALAR_TYPES[entity.type], _value(entity), entity)
        else:
            raise ContextReductionError("unsupported entity type: " + entity.type)

    def _location(self, context, entity):
        role = entity.attributes.get("role")
        field_name = {"pickup": "pickup_location", "dropoff": "dropoff_location"}.get(role)
        if not field_name:
            raise ContextReductionError("location entity requires pickup or dropoff role")
        self._single(context, field_name, dict(entity.attributes), entity)

    def _person(self, context, entity):
        role = entity.attributes.get("role")
        if role not in ("sender", "receiver"):
            raise ContextReductionError("person entity requires sender or receiver role")
        self._single(context, role, dict(entity.attributes), entity)

    def _phone(self, context, entity):
        role = entity.attributes.get("role")
        field_name = {"sender": "sender_phone", "receiver": "receiver_phone"}.get(role)
        if not field_name:
            raise ContextReductionError("phone entity requires sender or receiver role")
        self._single(context, field_name, _value(entity), entity)

    def _single(self, context, field_name: str, value: Any, entity: Entity):
        if entity.action in ("set", "replace"):
            setattr(context, field_name, value)
        elif entity.action == "remove":
            setattr(context, field_name, None)
        elif entity.action == "add":
            raise ContextReductionError("add is not supported for scalar field: " + field_name)

    def _cargo(self, context, entity: Entity):
        attrs = dict(entity.attributes)
        name = attrs.get("name") or entity.extraction_text
        index = next((i for i, item in enumerate(context.cargo) if item.get("name") == name), None)
        if entity.action in ("set", "replace"):
            item = attrs or {"name": name}
            item.setdefault("name", name)
            if index is None: context.cargo.append(item)
            else: context.cargo[index] = item
        elif entity.action == "remove":
            context.cargo = [item for item in context.cargo if item.get("name") != name]
        elif entity.action == "add":
            if index is None:
                context.cargo.append(attrs or {"name": name})
            else:
                current = context.cargo[index]
                for key, value in attrs.items():
                    current[key] = _add_measure(current[key], value) if key in ("weight", "quantity", "volume") and key in current else value

    def _list(self, context, field_name: str, value: Any, entity: Entity):
        values = value if isinstance(value, list) else [value]
        if entity.action in ("set", "replace"): setattr(context, field_name, list(values))
        elif entity.action == "add":
            current = getattr(context, field_name)
            for item in values:
                if item not in current: current.append(item)
        elif entity.action == "remove": setattr(context, field_name, [item for item in getattr(context, field_name) if item not in values])

    def _remark(self, context, entity):
        value = str(_value(entity))
        if entity.action in ("set", "replace"): context.remark = value
        elif entity.action == "add": context.remark = value if not context.remark else context.remark + ";" + value
        elif entity.action == "remove": context.remark = None if context.remark == value else context.remark


__all__ = ["ContextReductionError", "OrderContextReducer"]
