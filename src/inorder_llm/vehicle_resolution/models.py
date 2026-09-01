"""Models for final vehicle resolution."""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Mapping, Optional


@dataclass(frozen=True)
class VehicleResolutionResult:
    vehicle_type: str = ""
    vehicle_specs: List[str] = field(default_factory=list)
    source: str = "estimated"
    reason: str = ""
    raw_vehicle_text: str | None = None
    candidates: List[Mapping[str, Any]] = field(default_factory=list)
    effective_city: str | None = None
    vehicle_data_source: str | None = None
    catalog_version: str | None = None
    catalog_stale: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "vehicle_type": self.vehicle_type,
            "vehicle_specs": list(self.vehicle_specs),
            "source": self.source,
            "reason": self.reason,
            **({"raw_vehicle_text": self.raw_vehicle_text} if self.raw_vehicle_text else {}),
            **({"candidates": [dict(item) for item in self.candidates]} if self.candidates else {}),
            **({"effective_city": self.effective_city} if self.effective_city else {}),
            **({"vehicle_data_source": self.vehicle_data_source} if self.vehicle_data_source else {}),
            **({"catalog_version": self.catalog_version} if self.catalog_version else {}),
            **({"catalog_stale": True} if self.catalog_stale else {}),
        }


class VehicleResolutionError(ValueError):
    pass


class VehicleResolutionModel:
    def resolve(
        self,
        cargo_profiles: List[Mapping[str, Any]],
        cargo_profile_summary: Mapping[str, Any] | None,
        raw_vehicle_text: str | None = None,
    ) -> VehicleResolutionResult:
        raise NotImplementedError


__all__ = ["VehicleResolutionResult", "VehicleResolutionError", "VehicleResolutionModel"]
