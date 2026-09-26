## 1. Enforce vehicle context provenance

- [x] 1.1 Update `OrderContextReducer` so only a successfully matched explicit `vehicle_type` sets `vehicle_source="user_matched"`; matched `vehicle_specs` must not change the source.
- [x] 1.2 Handle vehicle `remove` and unmatched explicit `replace` before the generic normalization-rejection skip; clear both active type and source while preserving unmatched raw text for this turn.
- [x] 1.3 Preserve an existing canonical vehicle for unmatched expressions without explicit replacement intent, and normalize legacy nonempty type with missing source according to the design compatibility rule.
- [x] 1.4 Keep `OrderContext.vehicle_specs` limited to user-provided specifications and ensure specification set/replace/remove actions do not alter vehicle provenance.

## 2. Align vehicle resolution with source lifecycle

- [x] 2.1 Make `VehicleResolutionNode` use `vehicle_source` as the sole decision for the user-selected shortcut; a nonempty user-matched type must return directly without calling the fit resolver.
- [x] 2.2 Pass persisted user-provided specifications into the resolver result and keep cargo-derived specifications in `VehicleResolutionResult` without writing them back into `OrderContext.vehicle_specs`.
- [x] 2.3 Commit an estimated type only from a `lower_bound_fit` primary candidate; when no such primary exists, clear an old estimated type and source while retaining candidates and explanation.
- [x] 2.4 Preserve the existing `OrderGraph` topology and verify cargo-profile, pickup-city, user-specification, remove, and unmatched-replace inputs reach resolution with current context.

## 3. Verify behavior and specifications

- [x] 3.1 Add reducer tests for matched type provenance, specs-only updates, matched removal, unmatched replacement, non-replacement ambiguity, and legacy source normalization.
- [x] 3.2 Add graph tests for user-matched persistence across cargo changes, replacing a prior type with a new matched type, estimated recomputation after dependency changes, and clearing an estimate with no lower-bound primary.
- [x] 3.3 Add resolver/result tests proving user specifications are retained, cargo-derived specifications are not persisted into context, and upper-bound-only candidates remain recommendations without becoming the active type.
- [x] 3.4 Run focused vehicle/context tests, the full test suite, and strict OpenSpec validation; resolve any failures before marking the change ready to apply.
