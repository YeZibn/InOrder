## 1. Prompt and aggregation contract

- [x] 1.1 Update `CARGO_PROFILE_SYSTEM_PROMPT` to define repeated raw arrays as additive detail records, including explicit mixed-unit and repeated-weight examples.
- [x] 1.2 State that profile values must be calculated from the complete raw cargo snapshot and that previous profiles are never an input or accumulation source.

## 2. Result validation and atomic update

- [x] 2.1 Add deterministic validation for profile-to-summary arithmetic consistency with a documented floating-point tolerance.
- [x] 2.2 Validate explicit parseable raw weight/quantity/volume totals are not undercounted by the generated profile where the field is present.
- [x] 2.3 Preserve atomic replacement and previous context on profile validation or backend failure.

## 3. Tests and verification

- [x] 3.1 Add resolver tests for repeated same-cargo weights (`["1吨", "1吨"]`), mixed units, and multiple cargo names.
- [x] 3.2 Add tests asserting raw `cargo` remains unchanged while derived profiles are rebuilt from the full snapshot.
- [x] 3.3 Add tests for summary/profile consistency and rejection or repair of undercounted results.
- [x] 3.4 Run the cargo-profile, context, order-processing, and full test suites.
