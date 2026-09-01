"""Vehicle catalog providers, snapshots, and resilient in-process caching."""

from __future__ import annotations

import json
import threading
import time
import urllib.request
from dataclasses import dataclass
from typing import Any, Mapping, Protocol

from .vehicles import VEHICLE_SPECS, VEHICLE_TYPES, VehicleSpec, VehicleType


@dataclass(frozen=True)
class VehicleCatalogSnapshot:
    vehicle_types: tuple[VehicleType, ...]
    vehicle_specs: tuple[VehicleSpec, ...]
    city: str | None = None
    source: str = "global_default"
    version: str | None = None
    catalog_stale: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "city": self.city,
            "source": self.source,
            "version": self.version,
            "catalog_stale": self.catalog_stale,
            "vehicles": [item.to_dict() for item in self.vehicle_types],
            "specs": [item.to_dict() for item in self.vehicle_specs],
        }


class VehicleCatalogProvider(Protocol):
    def get_catalog(self, city: str | None = None, fallback: bool = True) -> VehicleCatalogSnapshot:
        ...


def normalize_city(value: str | None) -> str | None:
    if not isinstance(value, str):
        return None
    text = "".join(value.strip().split())
    if not text:
        return None
    for suffix in ("特别行政区", "自治州", "地区", "市", "省"):
        if text.endswith(suffix) and len(text) > len(suffix):
            text = text[: -len(suffix)]
            break
    # For qualified names such as “浙江省温州市”, retain the terminal city.
    if "省" in text:
        text = text.rsplit("省", 1)[-1]
    return text or None


class LocalVehicleCatalogProvider:
    """Local immutable snapshot used as global fallback and in tests."""

    def __init__(self, version: str = "local"):
        self.snapshot = VehicleCatalogSnapshot(tuple(VEHICLE_TYPES), tuple(VEHICLE_SPECS), None, "global_default", version)

    def get_catalog(self, city: str | None = None, fallback: bool = True) -> VehicleCatalogSnapshot:
        return self.snapshot


class RpcVehicleCatalogProvider:
    """HTTP JSON RPC adapter; transport details stay outside business logic."""

    def __init__(self, endpoint: str, timeout: float = 0.8, retries: int = 1):
        self.endpoint = endpoint.rstrip("/")
        self.timeout = timeout
        self.retries = max(0, retries)

    def get_catalog(self, city: str | None = None, fallback: bool = True) -> VehicleCatalogSnapshot:
        query = {"city": normalize_city(city), "fallback": fallback}
        body = json.dumps(query, ensure_ascii=False).encode("utf-8")
        request = urllib.request.Request(self.endpoint, data=body, headers={"Content-Type": "application/json"}, method="POST")
        last: Exception | None = None
        for _ in range(self.retries + 1):
            try:
                with urllib.request.urlopen(request, timeout=self.timeout) as response:
                    payload = json.loads(response.read().decode("utf-8"))
                return snapshot_from_payload(payload, normalize_city(city))
            except Exception as exc:  # pragma: no cover - network-specific
                last = exc
        raise RuntimeError("vehicle catalog RPC failed") from last


def snapshot_from_payload(payload: Mapping[str, Any], requested_city: str | None = None) -> VehicleCatalogSnapshot:
    """Decode the stable wire shape into existing catalog dataclasses."""
    from .vehicles import _pair
    types = []
    for row in payload.get("vehicles", payload.get("vehicle_types", [])):
        types.append(VehicleType(row["code"], row["label"], row.get("category", ""), tuple(row.get("aliases", [])), row.get("status", "active"), row.get("length_cm"), _pair(row.get("length_m"), "length_m"), _pair(row.get("width_m"), "width_m"), _pair(row.get("height_m"), "height_m"), _pair(row.get("volume_m3"), "volume_m3"), _pair(row.get("payload_t"), "payload_t")))
    specs = [VehicleSpec(row["code"], row["label"], row.get("group", ""), tuple(row.get("aliases", [])), row.get("status", "active")) for row in payload.get("specs", payload.get("vehicle_specs", []))]
    return VehicleCatalogSnapshot(tuple(types), tuple(specs), normalize_city(payload.get("city") or requested_city), payload.get("source", "global_default"), payload.get("data_version", payload.get("version")), bool(payload.get("catalog_stale", False)))


class CachedVehicleCatalogProvider:
    """TTL cache with per-city single-flight refresh and graceful fallback."""

    def __init__(self, remote: VehicleCatalogProvider, fallback: VehicleCatalogProvider | None = None, ttl_seconds: float = 300.0):
        self.remote, self.fallback, self.ttl_seconds = remote, fallback or LocalVehicleCatalogProvider(), ttl_seconds
        self._cache: dict[str | None, tuple[VehicleCatalogSnapshot, float]] = {}
        self._locks: dict[str | None, threading.RLock] = {}
        self._guard = threading.RLock()

    def _lock_for(self, city: str | None) -> threading.RLock:
        with self._guard:
            return self._locks.setdefault(city, threading.RLock())

    def get_catalog(self, city: str | None = None, fallback: bool = True) -> VehicleCatalogSnapshot:
        key = normalize_city(city)
        now = time.monotonic()
        cached = self._cache.get(key)
        if cached and cached[1] > now:
            return cached[0]
        lock = self._lock_for(key)
        with lock:
            cached = self._cache.get(key)
            if cached and cached[1] > time.monotonic():
                return cached[0]
            try:
                snapshot = self.remote.get_catalog(key, fallback)
                self._cache[key] = (snapshot, time.monotonic() + self.ttl_seconds)
                return snapshot
            except Exception:
                if cached:
                    stale = VehicleCatalogSnapshot(cached[0].vehicle_types, cached[0].vehicle_specs, cached[0].city, "stale_city_cache", cached[0].version, True)
                    self._cache[key] = (stale, time.monotonic() + self.ttl_seconds)
                    return stale
                snapshot = self.fallback.get_catalog(None, True)
                return VehicleCatalogSnapshot(snapshot.vehicle_types, snapshot.vehicle_specs, key, "local_fallback", snapshot.version, False)


__all__ = ["VehicleCatalogSnapshot", "VehicleCatalogProvider", "LocalVehicleCatalogProvider", "RpcVehicleCatalogProvider", "CachedVehicleCatalogProvider", "normalize_city", "snapshot_from_payload"]
