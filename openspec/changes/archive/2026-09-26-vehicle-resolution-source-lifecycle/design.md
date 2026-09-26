## Context

See `proposal.md` for motivation and the behavior contract in `specs/vehicle-resolution-and-estimation/spec.md`.

The current context already has one `vehicle_type`, `vehicle_specs`, and `vehicle_source`. The reducer sets `user_matched` for both matched vehicle types and matched specifications. `VehicleResolutionNode` also infers user selection from current-turn vehicle entities or a missing source, and when estimation has no lower-bound primary it clears the returned result type without clearing an old estimated type from the context. The graph already profiles changed cargo before vehicle resolution and reaches vehicle resolution after context updates; the resolver currently derives some result specifications from cargo profiles and has no persisted user-spec input.

## Goals / Non-Goals

**Goals:**

- Make `vehicle_source` the sole authority for whether the current canonical type is user-selected or estimated.
- Keep user-requested specifications distinct from cargo-derived specifications while retaining both in the current resolution result.
- Revoke an active type only for a successfully matched new type, explicit remove, or explicit unmatched replacement; clear stale estimates when no new estimated primary exists.
- Preserve current candidate limits, lower/upper-bound classification, ordering, catalog selection, and graph topology.

**Non-Goals:**

- Add separate persisted fields for user-selected and estimated types.
- Change vehicle capability ranges, packing, reserve policy, or candidate ranking.
- Add a catalog mapping between vehicle types and specifications. Specifications remain explicit requirements/result metadata; this change does not invent compatibility data that the catalog does not contain.
- Redesign extraction or add token-level progress.

## Decisions

### Keep one active vehicle and make source authoritative

`OrderContext.vehicle_type` remains the sole active canonical type. A matched explicit user type sets both the canonical value and `vehicle_source="user_matched"`; committing a lower-bound estimate sets the canonical value and `vehicle_source="estimated"`. An empty active type always has an empty context source. `VehicleResolutionResult.source` describes this turn's resolution and may be `estimated` while its `vehicle_type` is empty and the context has no active type; this preserves candidate/explanation provenance without claiming an active estimate.

The node SHALL return a matched user type directly only when both the canonical type is present and the source is `user_matched`. It SHALL NOT infer that a type is user-selected from the presence of any vehicle entity or from a missing source. This is simpler and safer than retaining parallel user/estimated fields or reconstructing provenance from message text on every turn.

For a legacy input context that contains a canonical type but no source, normalize it conservatively as `user_matched` for compatibility and to avoid silently overriding a possible explicit user choice. This is a one-time compatibility rule; new context writes must keep the type/source invariant. The trade-off is that a legacy estimate with missing provenance may be preserved until the user changes or removes it.

### Keep user specifications in context and derived specifications in results

`OrderContext.vehicle_specs` is the user's current specification list. The reducer owns its set/add/replace/remove actions and never changes `vehicle_source` while applying a specification. The resolver receives the persisted user specifications and combines them, with stable de-duplication, with specifications derived from cargo profiles for the current result. `VehicleResolutionNode` must not write resolver-derived specifications back into `OrderContext.vehicle_specs`.

The catalog currently has global specification entries but no per-vehicle compatibility mapping. Therefore this change preserves and reports specifications but does not add new candidate filtering by specification. Adding such a fit rule would require explicit catalog data and is outside this lifecycle change.

### Apply vehicle actions before deciding whether to estimate

The reducer handles vehicle type actions before its generic unmatched-entity early return:

- A matched `set` or `replace` writes the canonical type and `user_matched` source.
- A matched `remove` clears the type and source, while leaving independent user specifications intact.
- An unmatched expression with explicit `replace` intent clears the prior active type and source but is retained as raw input for this turn's estimate.
- An unmatched expression without replacement intent does not clear an active canonical type. In particular, a user-matched type remains locked and bypasses estimation.
- Specification actions update only the specification list.

This action-based rule prevents an ordinary question such as “大车是否合适” from discarding a selected vehicle while allowing “换成大车” to revoke it intentionally.

### Reuse the existing graph and estimate only when no user type is active

No graph node or edge is added. Cargo changes continue to trigger `CargoProfileNode`, followed by `VehicleResolutionNode`; pickup-city and specification changes already flow through context update to vehicle resolution. With `user_matched`, the node returns immediately without invoking the fit resolver. With no user-matched type, it resolves from the latest cargo profiles, summary, user specs, raw unmatched replacement text, and effective city. The current graph may still enter the resolution node on ordinary turns; avoiding repeated deterministic resolution is an optional optimization, not part of this change.

The resolver's existing lower-bound primary rule remains authoritative. On a lower-bound primary result, commit its canonical type and `estimated` source. If no lower-bound primary exists, including an upper-bound-only result or no candidates, clear an old active estimated type and source. Keep candidate details and explanation in `VehicleResolutionResult`; preserve user specifications in context.

## Risks / Trade-offs

- **A legacy context may have a type but no recoverable provenance** → Treat it as user-matched for compatibility, preserving user intent; test the normalization and document that this may temporarily preserve an old estimate.
- **User specifications have no catalog compatibility relation** → Preserve and report them without claiming that they filtered vehicle types; leave compatibility matching for a separately scoped catalog change.
- **Changing unmatched replace behavior could clear a user's previous selection** → Clear only when the extracted action explicitly denotes `replace` or `remove`; test questions and ordinary unmatched expressions separately.
- **Resolver implementations may have different call signatures** → Update the protocol and test doubles together, and keep any compatibility adapter narrowly scoped to the optional user-spec argument.

## Migration Plan

No `OrderContext` fields are added, so no persisted schema migration is required. On context entry, apply the legacy type-without-source compatibility rule. Deploy the reducer and resolution-node changes together so specs-only updates cannot mark an inferred type as user-matched and a failed estimate cannot leave an old inferred type active. Rollback is code-only: restore the previous reducer/node behavior; serialized fields remain readable because the context shape is unchanged.
