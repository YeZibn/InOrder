"""Static domain catalogs used by order extraction and later normalization.

The catalogs deliberately contain vocabulary only.  They do not infer a
vehicle from a vague expression and they do not decide which vehicle should
be selected for an order.
"""

from .vehicles import (
    VEHICLE_SPEC_CATALOG,
    VEHICLE_SPECS,
    VEHICLE_TYPE_CATALOG,
    VEHICLE_TYPES,
    VehicleSpec,
    VehicleType,
    VehicleKeyword,
    VehicleEntityType,
    VEHICLE_KEYWORDS,
    find_vehicle_spec,
    find_vehicle_type,
    get_vehicle_spec,
    get_vehicle_type,
    iter_vehicle_specs,
    iter_vehicle_types,
    find_vehicle_keyword,
    iter_vehicle_keywords,
    normalize_vehicle_keyword,
    render_vehicle_prompt_vocabulary,
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
    "find_vehicle_keyword",
    "iter_vehicle_keywords",
    "normalize_vehicle_keyword",
]
