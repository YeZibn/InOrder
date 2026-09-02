## 1. Extraction contract

- [x] 1.1 Add optional `province` to location Prompt, schema examples, and source-boundary rules.
- [x] 1.2 Validate and preserve province in LangExtract/JSON entity adapters without inferring missing values.

## 2. Context and API

- [x] 2.1 Persist province in pickup/dropoff OrderContext while preserving old payload compatibility.
- [x] 2.2 Ensure province is serialized through API/SSE and does not alter city-based vehicle selection.

## 3. Tests and verification

- [x] 3.1 Add explicit province, missing province, suffix normalization, and full-address grounding tests.
- [x] 3.2 Add context round-trip and legacy payload compatibility tests.
- [x] 3.3 Run extraction, context, workflow, and full test suites.
