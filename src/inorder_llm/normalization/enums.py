"""Supported order enum aliases and canonical values."""

from typing import Any, Dict, Mapping, Tuple

PAYMENT_TYPE_ALIASES: Mapping[str, int] = {
    "到付": 0,
    "货到付款": 0,
    "运费到付": 0,
    "预付": 1,
    "预付款": 1,
    "提前付款": 1,
    "先付款": 1,
}

INVOICE_TYPE_ALIASES: Mapping[str, int] = {
    "不开票": 1,
    "普票": 1,
    "电子普票": 1,
    "电子普通发票": 1,
    "专票": 2,
    "纸质专票": 2,
    "纸质增值税专用发票": 2,
}

SELF_FOLLOW_ALIASES: Mapping[str, int] = {
    "本人跟车": 1,
    "我跟车": 1,
    "自己跟车": 1,
    "本人随车": 1,
    "非本人跟车": 2,
    "他人跟车": 2,
    "别人跟车": 2,
    "司机跟车": 2,
    "不跟车": 2,
}

SERVICE_TYPE_ALIASES: Mapping[str, str] = {
    "快车": "express",
    "快速": "express",
    "快速送达": "express",
    "特快": "urgent",
    "加急": "urgent",
    "加急件": "urgent",
    "用户出价": "user_bid",
    "用户议价": "user_bid",
    "议价": "user_bid",
    "拼车": "shared",
    "顺风拼车": "shared",
}

ENUM_ALIASES: Mapping[str, Mapping[str, Any]] = {
    "payment_type": PAYMENT_TYPE_ALIASES,
    "invoice_type": INVOICE_TYPE_ALIASES,
    "oneself_follow_flag": SELF_FOLLOW_ALIASES,
    "service_type": SERVICE_TYPE_ALIASES,
}

CANONICAL_VALUES: Mapping[str, Tuple[Any, ...]] = {
    "payment_type": (0, 1),
    "invoice_type": (1, 2),
    "oneself_follow_flag": (1, 2),
    "service_type": ("express", "urgent", "user_bid", "shared"),
}

__all__ = ["ENUM_ALIASES", "CANONICAL_VALUES"]
