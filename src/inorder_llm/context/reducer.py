"""Apply extracted entity actions to an active order context."""

from copy import deepcopy
from typing import Any, Dict, Iterable, Mapping

from ..extract.models import Entity
from ..catalog import find_vehicle_spec, find_vehicle_type
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
}
_CARGO_RAW_FIELDS = ("weight", "quantity", "volume", "dimensions")


def _value(entity: Entity) -> Any:
    attrs = entity.attributes
    if "value" in attrs:
        return attrs["value"]
    return attrs.get("extraction_text") or entity.extraction_text


def _action(entity: Entity) -> str:
    value = entity.attributes.get("action")
    return value if value in ("add", "set", "remove", "replace") else entity.action


def _business_attributes(entity: Entity) -> Dict[str, Any]:
    return {key: value for key, value in entity.attributes.items() if key != "action"}


def _raw_values(value: Any) -> list[Any]:
    """Convert an extracted raw attribute into non-empty list entries."""

    if value is None:
        return []
    values = value if isinstance(value, (list, tuple)) else [value]
    result = []
    for item in values:
        if item is None:
            continue
        if isinstance(item, str) and not item.strip():
            continue
        result.append(item)
    return result


def _cargo_record(name: Any, attrs: Mapping[str, Any]) -> Dict[str, Any]:
    """Build the canonical raw cargo shape from one entity or legacy record."""

    record: Dict[str, Any] = {"name": name}
    for key, value in attrs.items():
        if key in ("name", *_CARGO_RAW_FIELDS):
            continue
        if value is not None:
            record[key] = value
    for field_name in _CARGO_RAW_FIELDS:
        record[field_name] = _raw_values(attrs.get(field_name))
    return record


class OrderContextReducer:
    """Pure reducer: returns a copied context and never calls external services."""

    def apply(self, context: OrderContext, entities: Iterable[Entity]) -> OrderContext:
        result = deepcopy(context)
        for entity in normalize_entities(entities):
            if entity.type in ("vehicle_type", "vehicle_specs") and entity.attributes.get("normalization_accepted") is False:
                continue
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
            self._single(context, "delivery_time", _business_attributes(entity), entity)
        elif entity.type == "cargo":
            self._cargo(context, entity)
        elif entity.type == "vehicle_specs":
            value = _value(entity)
            # Extract now preserves source expressions.  Until the dedicated
            # vehicle normalizer runs, unresolved expressions must not be
            # mistaken for canonical context values.
            record = find_vehicle_spec(value)
            if record is not None:
                context.vehicle_source = "user_matched"
                self._list(context, "vehicle_specs", record.code, entity)
        elif entity.type == "remark":
            self._remark(context, entity)
        elif entity.type in _SCALAR_TYPES:
            value = _value(entity)
            if entity.type == "vehicle_type":
                record = find_vehicle_type(value)
                if record is None:
                    return
                value = record.code
                context.vehicle_source = "user_matched"
            self._single(context, _SCALAR_TYPES[entity.type], value, entity)
        else:
            raise ContextReductionError("unsupported entity type: " + entity.type)

    def _location(self, context, entity):
        role = entity.attributes.get("role")
        field_name = {"pickup": "pickup_location", "dropoff": "dropoff_location"}.get(role)
        if not field_name:
            raise ContextReductionError("location entity requires pickup or dropoff role")
        self._single(context, field_name, _business_attributes(entity), entity)

    def _person(self, context, entity):
        role = entity.attributes.get("role")
        if role not in ("sender", "receiver"):
            raise ContextReductionError("person entity requires sender or receiver role")
        self._single(context, role, _business_attributes(entity), entity)

    def _phone(self, context, entity):
        role = entity.attributes.get("role")
        field_name = {"sender": "sender_phone", "receiver": "receiver_phone"}.get(role)
        if not field_name:
            raise ContextReductionError("phone entity requires sender or receiver role")
        self._single(context, field_name, _value(entity), entity)

    def _single(self, context, field_name: str, value: Any, entity: Entity):
        action = _action(entity)
        if action in ("set", "replace"):
            setattr(context, field_name, value)
        elif action == "remove":
            setattr(context, field_name, None)
        elif action == "add":
            raise ContextReductionError("add is not supported for scalar field: " + field_name)

    def _cargo(self, context, entity: Entity):
        context.cargo = [
            _cargo_record(item.get("name"), item)
            for item in context.cargo
        ]
        attrs = _business_attributes(entity)
        name = attrs.get("name") or entity.extraction_text
        index = next((i for i, item in enumerate(context.cargo) if item.get("name") == name), None)
        action = _action(entity)
        if action in ("set", "replace"):
            item = _cargo_record(name, attrs)
            if index is None: context.cargo.append(item)
            else: context.cargo[index] = item
        elif action == "remove":
            context.cargo = [item for item in context.cargo if item.get("name") != name]
        elif action == "add":
            if index is None:
                context.cargo.append(_cargo_record(name, attrs))
            else:
                current = _cargo_record(name, context.cargo[index])
                for field_name in _CARGO_RAW_FIELDS:
                    current[field_name].extend(_raw_values(attrs.get(field_name)))
                context.cargo[index] = current

    def _list(self, context, field_name: str, value: Any, entity: Entity):
        values = value if isinstance(value, list) else [value]
        action = _action(entity)
        if action in ("set", "replace"): setattr(context, field_name, list(values))
        elif action == "add":
            current = getattr(context, field_name)
            for item in values:
                if item not in current: current.append(item)
        elif action == "remove": setattr(context, field_name, [item for item in getattr(context, field_name) if item not in values])

    def _remark(self, context, entity):
        value = str(_value(entity))
        action = _action(entity)
        if action in ("set", "replace"): context.remark = value
        elif action == "add": context.remark = value if not context.remark else context.remark + ";" + value
        elif action == "remove": context.remark = None if context.remark == value else context.remark


__all__ = ["ContextReductionError", "OrderContextReducer"]
