"""Stable vehicle type and vehicle specification vocabulary.

This module is intentionally data-only.  A record's ``code`` is the value
that extraction prompts should place in ``attributes.value``; ``label`` and
``aliases`` are the values shown to users or recognized in natural language.
"""

import re
from dataclasses import dataclass
from typing import Dict, Iterable, Literal, Optional, Tuple

VehicleEntityType = Literal["vehicle_type", "vehicle_specs"]


@dataclass(frozen=True)
class VehicleType:
    """A base vehicle type or a standard vehicle length."""

    code: str
    label: str
    category: str
    aliases: Tuple[str, ...]
    status: str = "active"
    length_cm: Optional[int] = None

    def to_dict(self) -> Dict[str, object]:
        return {
            "code": self.code,
            "label": self.label,
            "category": self.category,
            "aliases": list(self.aliases),
            "status": self.status,
            "length_cm": self.length_cm,
        }


@dataclass(frozen=True)
class VehicleSpec:
    """A vehicle capability, body type, transport requirement, or equipment."""

    code: str
    label: str
    group: str
    aliases: Tuple[str, ...]
    status: str = "active"

    def to_dict(self) -> Dict[str, object]:
        return {
            "code": self.code,
            "label": self.label,
            "group": self.group,
            "aliases": list(self.aliases),
            "status": self.status,
        }


@dataclass(frozen=True)
class VehicleKeyword:
    """A high-confidence keyword that maps to exactly one catalog code."""

    entity_type: VehicleEntityType
    code: str
    label: str
    keywords: Tuple[str, ...]
    enabled: bool = True

    def to_dict(self) -> Dict[str, object]:
        return {
            "entity_type": self.entity_type,
            "code": self.code,
            "label": self.label,
            "keywords": list(self.keywords),
            "enabled": self.enabled,
        }


# Keep the tuple order stable: it is also the order used when presenting a
# catalog in a prompt or in an admin UI.
VEHICLE_TYPES: Tuple[VehicleType, ...] = (
    VehicleType("four_wheel_small", "四轮小件", "small_vehicle", ("四轮小件", "小拉")),
    VehicleType("micro_van", "微面", "van", ("微面",)),
    VehicleType("small_van", "小面", "van", ("小面", "小面包")),
    VehicleType("medium_van", "中面", "van", ("中面", "面包车")),
    VehicleType("large_van", "大面", "van", ("大面",)),
    VehicleType("iveco", "依维柯", "van", ("依维柯",)),
    VehicleType("micro_truck", "微货", "truck", ("微货",)),
    VehicleType("small_truck", "小货", "truck", ("小货",)),
    VehicleType("medium_truck", "中货", "truck", ("中货",)),
    VehicleType("truck_3m8", "3米8", "truck", ("3米8", "三米八", "3.8米"), length_cm=380),
    VehicleType("truck_4m2", "4米2", "truck", ("4米2", "四米二", "4.2米"), length_cm=420),
    VehicleType("truck_5m2", "5米2", "truck", ("5米2", "五米二", "5.2米"), length_cm=520),
    VehicleType("truck_6m2", "6米2", "truck", ("6米2", "六米二", "6.2米"), length_cm=620),
    VehicleType("truck_6m8", "6米8", "truck", ("6米8", "六米八", "6.8米"), length_cm=680),
    VehicleType("truck_7m6", "7米6", "truck", ("7米6", "七米六", "7.6米"), length_cm=760),
    VehicleType("truck_8m2", "8米2", "truck", ("8米2", "八米二", "8.2米"), length_cm=820),
    VehicleType("truck_8m6", "8米6", "truck", ("8米6", "八米六", "8.6米"), length_cm=860),
    VehicleType("truck_9m6", "9米6", "truck", ("9米6", "九米六", "9.6米"), length_cm=960),
    VehicleType("truck_11m7", "11米7", "truck", ("11米7", "十一米七", "11.7米"), length_cm=1170),
    VehicleType("truck_12m5", "12米5", "truck", ("12米5", "十二米五", "12.5米"), length_cm=1250),
    VehicleType("truck_13m", "13米", "truck", ("13米", "十三米"), length_cm=1300),
    VehicleType("truck_13m7", "13米7", "truck", ("13米7", "十三米七", "13.7米"), length_cm=1370),
    VehicleType("truck_15m", "15米", "truck", ("15米", "十五米"), length_cm=1500),
    VehicleType("truck_16m", "16米", "truck", ("16米", "十六米"), length_cm=1600),
    VehicleType("truck_17m5", "17米5", "truck", ("17米5", "十七米五", "17.5米"), length_cm=1750),
)


VEHICLE_SPECS: Tuple[VehicleSpec, ...] = (
    VehicleSpec(
        "cold_chain",
        "冷链",
        "temperature_control",
        ("冷链", "冷链车", "冷藏车", "冷冻车", "冷藏运输车"),
    ),
    VehicleSpec("enclosed", "厢式", "body_type", ("厢式", "厢式车", "封闭式", "封闭式车")),
    VehicleSpec("high_rail", "高栏", "body_type", ("高栏", "高栏车")),
    VehicleSpec("flatbed", "平板", "body_type", ("平板", "平板车")),
    VehicleSpec(
        "dangerous_goods",
        "危险品",
        "transport_requirement",
        ("危险品", "危险品车", "危化品车"),
    ),
    VehicleSpec("high_roof", "高顶", "structure", ("高顶", "高顶车")),
    VehicleSpec("tail_lift", "尾板", "loading_equipment", ("尾板", "带尾板", "尾板车")),
)


# Explicitly named aliases make the intended public API discoverable while
# keeping the underlying immutable tuples as the single source of truth.
VEHICLE_TYPE_CATALOG = VEHICLE_TYPES
VEHICLE_SPEC_CATALOG = VEHICLE_SPECS

_VEHICLE_TYPES_BY_CODE = {item.code: item for item in VEHICLE_TYPES}
_VEHICLE_SPECS_BY_CODE = {item.code: item for item in VEHICLE_SPECS}


def _keyword_tuple(item: object) -> Tuple[str, ...]:
    return tuple(dict.fromkeys((getattr(item, "label"), *getattr(item, "aliases"))))


def _length_keywords(item: VehicleType) -> Tuple[str, ...]:
    """Add only confirmed presentation variants for standard lengths."""

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
    [VehicleKeyword("vehicle_type", item.code, item.label, _length_keywords(item)) for item in VEHICLE_TYPES]
    + [VehicleKeyword("vehicle_specs", item.code, item.label, _keyword_tuple(item)) for item in VEHICLE_SPECS]
)


def _validate_keyword_catalog(records: Iterable[VehicleKeyword]) -> Dict[Tuple[VehicleEntityType, str], VehicleKeyword]:
    index: Dict[Tuple[VehicleEntityType, str], VehicleKeyword] = {}
    for record in records:
        if not record.keywords:
            raise ValueError(f"vehicle keyword record has no keywords: {record.code}")
        for keyword in record.keywords:
            key = (record.entity_type, normalize_vehicle_keyword(keyword))
            previous = index.get(key)
            if previous is not None and previous.code != record.code:
                raise ValueError(f"vehicle keyword collision: {keyword!r} maps to {previous.code} and {record.code}")
            index[key] = record
    return index


def _key(value: str) -> str:
    if not isinstance(value, str):
        return ""
    # Natural-language aliases commonly contain visual spacing.  Removing
    # whitespace is safe for these labels and does not introduce fuzzy match.
    return "".join(value.strip().split()).lower()


_FULLWIDTH_TRANSLATION = str.maketrans("０１２３４５６７８９．ｍＭ", "0123456789.mM")
_CN_DIGITS = {"零": "0", "一": "1", "二": "2", "三": "3", "四": "4", "五": "5", "六": "6", "七": "7", "八": "8", "九": "9"}


def normalize_vehicle_keyword(value: str) -> str:
    """Normalize harmless spelling variants without resolving range semantics."""

    if not isinstance(value, str):
        return ""
    text = value.translate(_FULLWIDTH_TRANSLATION).strip().lower()
    text = re.sub(r"\s+", "", text).replace("m", "米")
    # Convert the confirmed ``四米二`` style only; terms such as ``四米多``
    # intentionally remain untouched and therefore cannot match the catalog.
    text = re.sub(r"([一二三四五六七八九])米([一二三四五六七八九])", lambda m: f"{_CN_DIGITS[m.group(1)]}米{_CN_DIGITS[m.group(2)]}", text)
    return text


_VEHICLE_KEYWORD_INDEX = _validate_keyword_catalog(VEHICLE_KEYWORDS)


def iter_vehicle_keywords() -> Tuple[VehicleKeyword, ...]:
    return VEHICLE_KEYWORDS


def find_vehicle_keyword(value: str, entity_type: Optional[VehicleEntityType] = None) -> Optional[VehicleKeyword]:
    normalized = normalize_vehicle_keyword(value)
    if not normalized:
        return None
    if entity_type is not None:
        record = _VEHICLE_KEYWORD_INDEX.get((entity_type, normalized))
        return record if record is not None and record.enabled else None
    matches = [record for (kind, key), record in _VEHICLE_KEYWORD_INDEX.items() if key == normalized and record.enabled]
    if not matches:
        return None
    codes = {record.code for record in matches}
    return matches[0] if len(codes) == 1 else None


def get_vehicle_type(code: str) -> Optional[VehicleType]:
    """Return a vehicle type by its canonical code, or ``None`` if unknown."""

    return _VEHICLE_TYPES_BY_CODE.get(code)


def get_vehicle_spec(code: str) -> Optional[VehicleSpec]:
    """Return a vehicle specification by its canonical code, or ``None``."""

    return _VEHICLE_SPECS_BY_CODE.get(code)


def _find(value: str, records: Iterable[object]) -> Optional[object]:
    key = _key(value)
    for record in records:
        if _key(getattr(record, "code")) == key or _key(getattr(record, "label")) == key:
            return record
        if any(_key(alias) == key for alias in getattr(record, "aliases")):
            return record
    return None


def find_vehicle_type(value: str) -> Optional[VehicleType]:
    """Find a type by an exact code, label, or declared alias.

    Matching is intentionally exact after whitespace cleanup.  Expressions
    such as ``之前那个车`` or length ranges are not inferred here.
    """

    return _find(value, VEHICLE_TYPES)  # type: ignore[return-value]


def find_vehicle_spec(value: str) -> Optional[VehicleSpec]:
    """Find a specification by an exact code, label, or declared alias."""

    return _find(value, VEHICLE_SPECS)  # type: ignore[return-value]


def iter_vehicle_types() -> Tuple[VehicleType, ...]:
    """Return the immutable vehicle type catalog in stable order."""

    return VEHICLE_TYPES


def iter_vehicle_specs() -> Tuple[VehicleSpec, ...]:
    """Return the immutable vehicle specification catalog in stable order."""

    return VEHICLE_SPECS


def render_vehicle_prompt_vocabulary() -> str:
    """Render the catalog vocabulary used by extraction prompts.

    This is deliberately a presentation helper rather than a matcher: the
    catalog remains the sole source of labels and aliases, while extraction
    still preserves the expression used by the user.
    """

    type_lines = []
    for item in VEHICLE_TYPES:
        aliases = "、".join(item.aliases)
        type_lines.append(f"- {item.label}（{item.code}）：{aliases}")
    spec_lines = []
    for item in VEHICLE_SPECS:
        aliases = "、".join(item.aliases)
        spec_lines.append(f"- {item.label}（{item.code}）：{aliases}")
    return (
        "基础车型/标准车长词汇（仅用于识别和分类，输出保留用户原文）：\n"
        + "\n".join(type_lines)
        + "\n车辆规格词汇（仅用于识别和分类，输出保留用户原文）：\n"
        + "\n".join(spec_lines)
    )


__all__ = [
    "VehicleType",
    "VehicleSpec",
    "VehicleKeyword",
    "VehicleEntityType",
    "VEHICLE_TYPES",
    "VEHICLE_SPECS",
    "VEHICLE_TYPE_CATALOG",
    "VEHICLE_SPEC_CATALOG",
    "get_vehicle_type",
    "get_vehicle_spec",
    "find_vehicle_type",
    "find_vehicle_spec",
    "iter_vehicle_types",
    "iter_vehicle_specs",
    "render_vehicle_prompt_vocabulary",
    "VEHICLE_KEYWORDS",
    "normalize_vehicle_keyword",
    "find_vehicle_keyword",
    "iter_vehicle_keywords",
]
