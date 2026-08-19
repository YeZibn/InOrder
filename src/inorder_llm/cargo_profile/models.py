"""JSON-compatible models for derived cargo constraints."""

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
class QuantityProfile:
    value: Optional[float] = None
    unit: str = "unknown"
    raw: List[Any] = field(default_factory=list)
    basis: str = "unknown"
    confidence: str = "unknown"

    def to_dict(self) -> Dict[str, Any]:
        return _clean(self.__dict__.copy())


@dataclass
class WeightProfile:
    total_kg: Optional[float] = None
    per_unit_kg: Optional[float] = None
    raw: List[Any] = field(default_factory=list)
    basis: str = "unknown"
    confidence: str = "unknown"

    def to_dict(self) -> Dict[str, Any]:
        return _clean(self.__dict__.copy())


@dataclass
class DimensionsProfile:
    length_cm: Optional[float] = None
    width_cm: Optional[float] = None
    height_cm: Optional[float] = None
    scope: str = "unknown"
    shape: str = "unknown"
    raw: List[Any] = field(default_factory=list)
    basis: str = "unknown"
    confidence: str = "unknown"

    def to_dict(self) -> Dict[str, Any]:
        return _clean(self.__dict__.copy())


@dataclass
class VolumeProfile:
    unit_m3: Optional[float] = None
    total_m3: Optional[float] = None
    raw: List[Any] = field(default_factory=list)
    basis: str = "unknown"
    confidence: str = "unknown"

    def to_dict(self) -> Dict[str, Any]:
        return _clean(self.__dict__.copy())


@dataclass
class TransportProperty:
    value: str = "unknown"
    basis: str = "unknown"
    confidence: str = "unknown"
    reason: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return _clean(self.__dict__.copy())


@dataclass
class CargoProfile:
    name: str
    quantity: Mapping[str, Any]
    weight: Mapping[str, Any]
    dimensions: Mapping[str, Any]
    volume: Mapping[str, Any]
    stackability: Mapping[str, Any]
    fragility: Mapping[str, Any]
    temperature: Mapping[str, Any]
    assumptions: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return _clean(self.__dict__.copy())


@dataclass
class CargoProfileSummary:
    total_weight_kg: Optional[float] = None
    total_volume_m3: Optional[float] = None
    weight_status: str = "unknown"
    volume_status: str = "unknown"
    confidence: str = "unknown"
    warnings: List[str] = field(default_factory=list)

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


__all__ = [
    "QuantityProfile", "WeightProfile", "DimensionsProfile", "VolumeProfile",
    "TransportProperty", "CargoProfile", "CargoProfileSummary",
    "CargoProfileResult",
]
