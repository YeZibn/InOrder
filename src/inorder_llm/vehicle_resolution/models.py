"""Models for final vehicle resolution."""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Mapping


@dataclass(frozen=True)
class VehicleResolutionResult:
    vehicle_type: str
    vehicle_specs: List[str] = field(default_factory=list)
    source: str = "estimated"
    reason: str = ""
    raw_vehicle_text: str | None = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "vehicle_type": self.vehicle_type,
            "vehicle_specs": list(self.vehicle_specs),
            "source": self.source,
            "reason": self.reason,
            **({"raw_vehicle_text": self.raw_vehicle_text} if self.raw_vehicle_text else {}),
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
