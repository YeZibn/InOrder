"""Compact JSON-compatible cargo constraint profiles."""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Mapping, Optional


def _clean(value: Any) -> Any:
    if hasattr(value, "to_dict"):
        return value.to_dict()
    if isinstance(value, list):
        return [_clean(item) for item in value]
    if isinstance(value, dict):
        return {key: _clean(item) for key, item in value.items()}
    return value


@dataclass
class CargoProfile:
    name: str
    weight_kg: Optional[float]
    volume_m3: Optional[float]
    dimensions_cm: Mapping[str, Optional[float]]
    stackability: str
    fragility: str
    temperature: str
    reason: str

    def to_dict(self) -> Dict[str, Any]:
        return _clean(self.__dict__.copy())


@dataclass
class CargoProfileSummary:
    total_weight_kg: Optional[float] = None
    total_volume_m3: Optional[float] = None
    reason: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return _clean(self.__dict__.copy())


@dataclass
class CargoProfileResult:
    cargo_profiles: List[CargoProfile]
    cargo_profile_summary: CargoProfileSummary

    def to_dict(self) -> Dict[str, Any]:
        return {
            "cargo_profiles": [_clean(item) for item in self.cargo_profiles],
            "cargo_profile_summary": _clean(self.cargo_profile_summary),
        }


# Kept as aliases for callers that imported the old names; the compact schema
# intentionally does not serialize these legacy field-level models.
@dataclass
class DimensionsProfile:
    length_cm: Optional[float] = None
    width_cm: Optional[float] = None
    height_cm: Optional[float] = None


@dataclass
class QuantityProfile:
    value: Optional[float] = None


@dataclass
class WeightProfile:
    total_kg: Optional[float] = None


@dataclass
class VolumeProfile:
    total_m3: Optional[float] = None


@dataclass
class TransportProperty:
    value: str = "unknown"


__all__ = [
    "CargoProfile", "CargoProfileResult", "CargoProfileSummary",
    "DimensionsProfile", "QuantityProfile", "TransportProperty",
    "VolumeProfile", "WeightProfile",
]
