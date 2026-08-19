## 1. Profile data model

- [x] 1.1 Add JSON-compatible cargo profile models for quantity, weight, dimensions, volume, stackability, fragility, and temperature.
- [x] 1.2 Add optional `cargo_profiles` and `cargo_profile_summary` fields to `OrderContext` without changing raw cargo list semantics.
- [x] 1.3 Add serialization and backward-compatibility tests for contexts with and without derived profiles.

## 2. LLM profile resolver

- [x] 2.1 Define an injectable cargo-profile backend/resolver protocol accepting the complete raw cargo snapshot.
- [x] 2.2 Write a strict JSON prompt that distinguishes explicit, derived, estimated, and unknown values and requires assumptions/confidence/warnings.
- [x] 2.3 Implement LLM response parsing and contract validation for all profile fields and summary totals.
- [x] 2.4 Ensure resolver never mutates raw cargo and never emits vehicle selection, vehicle codes, or packing coordinates.

## 3. Context integration

- [x] 3.1 Add a pure profile update operation that regenerates profiles from the complete current cargo collection.
- [x] 3.2 Replace profiles and summary atomically after successful generation; preserve the previous profile or clear it according to the defined failure behavior without changing raw cargo.
- [x] 3.3 Expose profile output through existing context serialization/CLI inspection surfaces where applicable.

## 4. Verification

- [x] 4.1 Test explicit weight/volume/dimensions precedence and raw-expression preservation.
- [x] 4.2 Test unknown and partial estimates, confidence, assumptions, and warnings.
- [x] 4.3 Test stackability, fragility, and temperature enum validation.
- [x] 4.4 Test full regeneration after cargo add/replace/remove without double-counting old derived values.
- [x] 4.5 Run the full test suite in the conda `agent` environment.
