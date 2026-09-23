## Context

See `proposal.md` and `specs/` for the behavior contract. The resolver currently takes the upper endpoint of each vehicle range, returns a boolean `fit`, sorts candidates by upper-bound slack and commits the first candidate to the order context. Cargo boxes are evaluated by the existing greedy extreme-point search.

The stored ranges are estimates used by the current application. This change distinguishes results relative to those stored ranges; it does not certify the capacity of a specific physical vehicle.

## Goals / Non-Goals

**Goals:**

- Evaluate each candidate at the stored lower and upper endpoints.
- Put lower-bound candidates first and include upper-bound-only candidates at a lower rank.
- Prefer the smallest sufficient candidate within each rank and cap the result at three.
- Prevent an upper-bound-only candidate from becoming the estimated vehicle in order context.

**Non-Goals:**

- Changing vehicle master data, catalog providers, RPC payloads or range values.
- Adding a new universal reserve percentage or vehicle-specific reserve policy.
- Replacing the existing packing heuristic with an optimal 3D solver.
- Certifying real-world loading, splitting cargo across vehicles, or estimating price and availability.

## Decisions

1. **Run the existing checks at both endpoints.** Pass the lower endpoint of every scalar range and dimension range through the same weight, volume and packing checks, then repeat with upper endpoints. The lower result is `lower_bound_fit`; a candidate that fails there but passes at the upper endpoint is `upper_bound_only`. This avoids the current upper-only hard decision. The alternative of keeping upper-only evaluation is rejected because it still treats the optimistic case as ordinary fit.

2. **Keep both levels in one ranked shortlist.** Sort `lower_bound_fit` before `upper_bound_only`; within each level, sort by smallest sufficient capacity using the corresponding endpoint slack and stable vehicle code as a tie-breaker. Return at most three, filling remaining slots with upper-only candidates when available. Excluding upper-only candidates was considered, but would hide useful choices when the conservative shortlist is short or empty.

3. **Keep candidate status distinct from the primary vehicle.** A lower-bound candidate may become the estimated primary vehicle. Upper-only candidates stay in the recommendations but do not set the primary `vehicle_type` or overwrite an existing canonical vehicle in context. A matched user vehicle remains unchanged.

4. **Use the stored lower endpoint as the conservative case for this change.** Do not layer an unsupported fixed utilization percentage on top. Missing box dimensions must prevent a lower-bound fit instead of causing the box to be skipped. The existing packing heuristic remains in place; a result describes its calculation against the stored profile and range, not a loading certification.

## Risks / Trade-offs

- [Stored ranges may be estimates rather than verified guarantees] → Label results by the endpoint used and describe them as calculations against current catalog values, not physical certification.
- [The upper endpoints of different fields may not describe one real vehicle] → Keep upper-only candidates clearly marked as possible and below all lower-bound candidates.
- [The greedy packing heuristic can miss valid arrangements] → Keep the existing behavior and scope; do not add claims of globally complete packing in this change.
- [Lower-bound results may be fewer than three] → Fill the remaining shortlist with upper-only candidates, preserving their lower confidence label.

## Migration Plan

1. Update the resolver to calculate both endpoints and return a fit level for each candidate.
2. Update ordering and result serialization so lower-bound candidates rank first and at most three candidates are returned.
3. Update order-context write-back and CLI rendering; only a lower-bound primary candidate is committed.
4. Add focused tests for both boundaries, tier ordering, shortlist size, missing dimensions and context preservation.

No catalog migration or external data rollout is required.
