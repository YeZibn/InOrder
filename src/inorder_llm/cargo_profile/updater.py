"""Pure, atomic replacement of derived cargo profiles."""

from copy import deepcopy
from typing import Protocol

from ..context.models import OrderContext
from .models import CargoProfileResult


class CargoProfileBackend(Protocol):
    def profile(self, cargo) -> CargoProfileResult:
        ...


def regenerate_cargo_profile(context: OrderContext, backend: CargoProfileBackend) -> OrderContext:
    """Return a copied context with profiles rebuilt from the complete raw cargo.

    The input is never mutated. If the backend raises, no partially updated
    context is returned and the caller can retain the previous context.
    """
    result = deepcopy(context)
    if not result.cargo:
        result.cargo_profiles = []
        result.cargo_profile_summary = None
        return result
    generated = backend.profile(deepcopy(result.cargo))
    payload = generated.to_dict() if hasattr(generated, "to_dict") else generated
    result.cargo_profiles = deepcopy(payload["cargo_profiles"])
    result.cargo_profile_summary = deepcopy(payload["cargo_profile_summary"])
    return result


class CargoProfileUpdater:
    def __init__(self, backend: CargoProfileBackend):
        self.backend = backend

    def update(self, context: OrderContext) -> OrderContext:
        return regenerate_cargo_profile(context, self.backend)


__all__ = ["CargoProfileBackend", "CargoProfileUpdater", "regenerate_cargo_profile"]
