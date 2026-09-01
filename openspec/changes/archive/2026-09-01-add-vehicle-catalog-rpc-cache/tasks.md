## 1. Provider and data model

- [x] 1.1 Define a unified vehicle catalog snapshot/provider protocol preserving existing lookup and prompt vocabulary APIs.
- [x] 1.2 Wrap the existing `vehicles.json` as the local global-fallback provider.
- [x] 1.3 Define versioned city override and catalog response models with source/stale metadata.

## 2. City resolution and API contract

- [x] 2.1 Add optional `user_location.city` to the chat request and workflow state.
- [x] 2.2 Implement deterministic city normalization and effective-city priority: pickup city, then user location, then global default.
- [x] 2.3 Pass effective city through order processing without changing cargo profiling or user vehicle-match semantics.

## 3. RPC client, cache, and fallback

- [x] 3.1 Implement RPC catalog client with configurable endpoint, short timeout, and one retry.
- [x] 3.2 Implement immutable in-memory per-city snapshots with TTL and catalog version metadata.
- [x] 3.3 Add city-level refresh locks, double-checking, and single-flight behavior for concurrent misses.
- [x] 3.4 Implement stale-city-cache and local-global fallback behavior on RPC failure.

## 4. Integrate vehicle consumers

- [x] 4.1 Update vehicle matching, normalization, context reduction, prompt vocabulary, and vehicle resolution to use the provider.
- [x] 4.2 Add effective-city, catalog-source, catalog-version, and stale metadata to vehicle resolution output.
- [x] 4.3 Preserve existing canonical codes and user-matched vehicle behavior.

## 5. Tests and rollout

- [x] 5.1 Add tests for city priority, aliases, missing-city fallback, and city overrides.
- [x] 5.2 Add cache hit, TTL expiry, concurrent refresh lock, stale cache, and local fallback tests.
- [x] 5.3 Add RPC timeout/retry and provider failure isolation tests.
- [x] 5.4 Run the full test suite and document RPC environment configuration and rollout/rollback behavior.
