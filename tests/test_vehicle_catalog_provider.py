import threading
import time

from inorder_llm.catalog.provider import (
    CachedVehicleCatalogProvider,
    LocalVehicleCatalogProvider,
    VehicleCatalogSnapshot,
    normalize_city,
)


def test_normalize_city_handles_qualified_names():
    assert normalize_city("浙江省温州市") == "温州"
    assert normalize_city(" 上海市 ") == "上海"


class CountingProvider:
    def __init__(self, delay=0):
        self.calls = 0
        self.delay = delay
        self.snapshot = LocalVehicleCatalogProvider().snapshot

    def get_catalog(self, city=None, fallback=True):
        self.calls += 1
        if self.delay:
            time.sleep(self.delay)
        return VehicleCatalogSnapshot(self.snapshot.vehicle_types, self.snapshot.vehicle_specs, city, "city_override", "v1")


def test_cache_collapses_concurrent_misses():
    remote = CountingProvider(delay=0.02)
    provider = CachedVehicleCatalogProvider(remote, ttl_seconds=60)
    results = []
    threads = [threading.Thread(target=lambda: results.append(provider.get_catalog("温州"))) for _ in range(8)]
    for thread in threads: thread.start()
    for thread in threads: thread.join()
    assert remote.calls == 1
    assert len(results) == 8 and all(item.version == "v1" for item in results)


def test_cache_uses_stale_snapshot_on_remote_failure():
    remote = CountingProvider()
    provider = CachedVehicleCatalogProvider(remote, ttl_seconds=0)
    first = provider.get_catalog("温州")
    remote.get_catalog = lambda city=None, fallback=True: (_ for _ in ()).throw(RuntimeError("down"))
    stale = provider.get_catalog("温州")
    assert first.source == "city_override"
    assert stale.source == "stale_city_cache" and stale.catalog_stale is True


def test_cache_uses_local_fallback_on_cold_failure():
    remote = CountingProvider()
    remote.get_catalog = lambda city=None, fallback=True: (_ for _ in ()).throw(RuntimeError("down"))
    result = CachedVehicleCatalogProvider(remote).get_catalog("温州")
    assert result.source == "local_fallback"
