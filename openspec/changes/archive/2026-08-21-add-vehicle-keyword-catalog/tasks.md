## 1. Keyword catalog model

- [x] 1.1 Define stable keyword record fields for entity type, code, label, keywords, and enabled status.
- [x] 1.2 Populate the 9 base vehicle, 16 standard length, and 7 vehicle specification mappings.
- [x] 1.3 Add normalized keyword indexing with deterministic collision detection and stable iteration order.

## 2. Matching contract

- [x] 2.1 Implement harmless text cleanup for spacing, full-width forms, `m`/`米`, and confirmed Chinese-number length variants.
- [x] 2.2 Ensure range, approximate, generic, and historical expressions do not resolve to a concrete code.
- [x] 2.3 Expose catalog readers for future normalization without changing Extract source preservation.

## 3. Verification

- [x] 3.1 Add tests for every confirmed vehicle category and representative aliases.
- [x] 3.2 Add tests for normalization variants, keyword uniqueness, stable serialization, and excluded ambiguous expressions.
- [x] 3.3 Run the full test suite in the `agent` conda environment and document the deterministic-only scope.
