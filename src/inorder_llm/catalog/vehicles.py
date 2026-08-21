"""Vehicle master-data facade.

The JSON file in ``catalog/data`` is the single source of truth.  This module
keeps the established immutable objects and lookup functions as a compatible
Python API for extraction and normalization callers.
"""

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, Literal, Optional, Tuple

VehicleEntityType = Literal["vehicle_type", "vehicle_specs"]


@dataclass(frozen=True)
class VehicleType:
    code: str
    label: str
    category: str
    aliases: Tuple[str, ...]
    status: str = "active"
    length_cm: Optional[int] = None
    length_m: Optional[Tuple[float, float]] = None
    width_m: Optional[Tuple[float, float]] = None
    height_m: Optional[Tuple[float, float]] = None
    volume_m3: Optional[Tuple[float, float]] = None
    payload_t: Optional[Tuple[float, float]] = None

    def to_dict(self) -> Dict[str, object]:
        return {"code": self.code, "label": self.label, "category": self.category,
                "aliases": list(self.aliases), "status": self.status,
                "length_cm": self.length_cm, "length_m": list(self.length_m) if self.length_m else None,
                "width_m": list(self.width_m) if self.width_m else None,
                "height_m": list(self.height_m) if self.height_m else None,
                "volume_m3": list(self.volume_m3) if self.volume_m3 else None,
                "payload_t": list(self.payload_t) if self.payload_t else None}


@dataclass(frozen=True)
class VehicleSpec:
    code: str
    label: str
    group: str
    aliases: Tuple[str, ...]
    status: str = "active"

    def to_dict(self) -> Dict[str, object]:
        return {"code": self.code, "label": self.label, "group": self.group,
                "aliases": list(self.aliases), "status": self.status}


@dataclass(frozen=True)
class VehicleKeyword:
    entity_type: VehicleEntityType
    code: str
    label: str
    keywords: Tuple[str, ...]
    enabled: bool = True

    def to_dict(self) -> Dict[str, object]:
        return {"entity_type": self.entity_type, "code": self.code, "label": self.label,
                "keywords": list(self.keywords), "enabled": self.enabled}


def _pair(value: object, field: str) -> Optional[Tuple[float, float]]:
    if value is None:
        return None
    if not isinstance(value, list) or len(value) != 2:
        raise ValueError(f"{field} must be a two-item range")
    result = (float(value[0]), float(value[1]))
    if result[0] > result[1]:
        raise ValueError(f"{field} range is descending")
    return result


def _load_master_data() -> Tuple[Tuple[VehicleType, ...], Tuple[VehicleSpec, ...]]:
    path = Path(__file__).with_name("data") / "vehicles.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    type_rows, spec_rows = payload.get("vehicle_types"), payload.get("vehicle_specs")
    if not isinstance(type_rows, list) or not isinstance(spec_rows, list):
        raise ValueError("vehicle master data must contain vehicle_types and vehicle_specs lists")
    types = []
    for row in type_rows:
        required = ("code", "label", "category", "aliases", "length_m", "width_m", "height_m", "volume_m3", "payload_t")
        if any(key not in row for key in required) or not row["aliases"]:
            raise ValueError(f"invalid vehicle type record: {row!r}")
        types.append(VehicleType(row["code"], row["label"], row["category"], tuple(row["aliases"]),
            length_cm=row.get("length_cm"), length_m=_pair(row["length_m"], "length_m"),
            width_m=_pair(row["width_m"], "width_m"), height_m=_pair(row["height_m"], "height_m"),
            volume_m3=_pair(row["volume_m3"], "volume_m3"), payload_t=_pair(row["payload_t"], "payload_t")))
    specs = []
    for row in spec_rows:
        if any(key not in row for key in ("code", "label", "group", "aliases")) or not row["aliases"]:
            raise ValueError(f"invalid vehicle spec record: {row!r}")
        specs.append(VehicleSpec(row["code"], row["label"], row["group"], tuple(row["aliases"])))
    if len({x.code for x in types}) != len(types) or len({x.code for x in specs}) != len(specs):
        raise ValueError("vehicle master data contains duplicate codes")
    return tuple(types), tuple(specs)


VEHICLE_TYPES, VEHICLE_SPECS = _load_master_data()
VEHICLE_TYPE_CATALOG = VEHICLE_TYPES
VEHICLE_SPEC_CATALOG = VEHICLE_SPECS


def _key(value: str) -> str:
    return "".join(value.strip().split()).lower() if isinstance(value, str) else ""


_FULLWIDTH_TRANSLATION = str.maketrans("０１２３４５６７８９．ｍＭ", "0123456789.mM")
_CN_DIGITS = {"零":"0", "一":"1", "二":"2", "三":"3", "四":"4", "五":"5", "六":"6", "七":"7", "八":"8", "九":"9"}


def normalize_vehicle_keyword(value: str) -> str:
    if not isinstance(value, str):
        return ""
    text = re.sub(r"\s+", "", value.translate(_FULLWIDTH_TRANSLATION).strip().lower()).replace("m", "米")
    return re.sub(r"([一二三四五六七八九])米([一二三四五六七八九])", lambda m: f"{_CN_DIGITS[m.group(1)]}米{_CN_DIGITS[m.group(2)]}", text)


def _keyword_tuple(item: object) -> Tuple[str, ...]:
    return tuple(dict.fromkeys((getattr(item, "label"), *getattr(item, "aliases"))))


def _length_keywords(item: VehicleType) -> Tuple[str, ...]:
    if item.length_cm is None:
        return _keyword_tuple(item)
    meters = item.length_cm / 100
    if item.length_cm % 100 == 0:
        numeric = f"{int(meters)}"
        return tuple(dict.fromkeys((*_keyword_tuple(item), f"{numeric}米", f"{numeric}m")))
    whole, decimal = divmod(item.length_cm, 100)
    numeric = f"{whole}.{decimal}"
    return tuple(dict.fromkeys((*_keyword_tuple(item), f"{numeric}米", f"{numeric}m", f"{whole}米{decimal}")))


VEHICLE_KEYWORDS: Tuple[VehicleKeyword, ...] = tuple(
    [VehicleKeyword("vehicle_type", x.code, x.label, _length_keywords(x)) for x in VEHICLE_TYPES]
    + [VehicleKeyword("vehicle_specs", x.code, x.label, _keyword_tuple(x)) for x in VEHICLE_SPECS]
)
_VEHICLE_TYPES_BY_CODE = {x.code: x for x in VEHICLE_TYPES}
_VEHICLE_SPECS_BY_CODE = {x.code: x for x in VEHICLE_SPECS}
_VEHICLE_KEYWORD_INDEX = {}
for record in VEHICLE_KEYWORDS:
    for keyword in record.keywords:
        key = (record.entity_type, normalize_vehicle_keyword(keyword))
        old = _VEHICLE_KEYWORD_INDEX.get(key)
        if old is not None and old.code != record.code:
            raise ValueError(f"vehicle keyword collision: {keyword!r}")
        _VEHICLE_KEYWORD_INDEX[key] = record


def iter_vehicle_keywords() -> Tuple[VehicleKeyword, ...]: return VEHICLE_KEYWORDS
def get_vehicle_type(code: str) -> Optional[VehicleType]: return _VEHICLE_TYPES_BY_CODE.get(code)
def get_vehicle_spec(code: str) -> Optional[VehicleSpec]: return _VEHICLE_SPECS_BY_CODE.get(code)


def _find(value: str, records: Iterable[object]) -> Optional[object]:
    key = _key(value)
    for record in records:
        if _key(getattr(record, "code")) == key or _key(getattr(record, "label")) == key or any(_key(a) == key for a in getattr(record, "aliases")):
            return record
    return None


def find_vehicle_type(value: str) -> Optional[VehicleType]: return _find(value, VEHICLE_TYPES)  # type: ignore[return-value]
def find_vehicle_spec(value: str) -> Optional[VehicleSpec]: return _find(value, VEHICLE_SPECS)  # type: ignore[return-value]
def iter_vehicle_types() -> Tuple[VehicleType, ...]: return VEHICLE_TYPES
def iter_vehicle_specs() -> Tuple[VehicleSpec, ...]: return VEHICLE_SPECS


def find_vehicle_keyword(value: str, entity_type: Optional[VehicleEntityType] = None) -> Optional[VehicleKeyword]:
    normalized = normalize_vehicle_keyword(value)
    if not normalized:
        return None
    if entity_type:
        return _VEHICLE_KEYWORD_INDEX.get((entity_type, normalized))
    matches = [r for (kind, key), r in _VEHICLE_KEYWORD_INDEX.items() if key == normalized]
    return matches[0] if matches and len({r.code for r in matches}) == 1 else None


def render_vehicle_prompt_vocabulary() -> str:
    types = "\n".join(f"- {x.label}（{x.code}）：{'、'.join(x.aliases)}" for x in VEHICLE_TYPES)
    specs = "\n".join(f"- {x.label}（{x.code}）：{'、'.join(x.aliases)}" for x in VEHICLE_SPECS)
    return "基础车型/标准车长词汇（仅用于识别和分类，输出保留用户原文）：\n" + types + "\n车辆规格词汇（仅用于识别和分类，输出保留用户原文）：\n" + specs


__all__ = ["VehicleType", "VehicleSpec", "VehicleKeyword", "VehicleEntityType", "VEHICLE_TYPES", "VEHICLE_SPECS", "VEHICLE_TYPE_CATALOG", "VEHICLE_SPEC_CATALOG", "get_vehicle_type", "get_vehicle_spec", "find_vehicle_type", "find_vehicle_spec", "iter_vehicle_types", "iter_vehicle_specs", "render_vehicle_prompt_vocabulary", "VEHICLE_KEYWORDS", "normalize_vehicle_keyword", "find_vehicle_keyword", "iter_vehicle_keywords"]
