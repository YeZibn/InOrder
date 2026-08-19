## 1. Location contract and prompts

- [x] 1.1 Update JSON extraction location contract to support `city` and `full_address` with conservative null/omission behavior.
- [x] 1.2 Update LangExtract location prompt description and examples for city-only and detailed addresses.
- [x] 1.3 Record the prompt change as a separate timestamped entry in `PROMPT_CHANGELOG.md`.

## 2. Extraction and context compatibility

- [x] 2.1 Ensure JSON resolver and LangExtract adapter preserve location role, grounded extraction text, and full address without local address inference.
- [x] 2.2 Verify `OrderContext` and reducer preserve `city` plus `full_address` for pickup and dropoff actions.

## 3. Verification

- [x] 3.1 Add tests for detailed pickup/dropoff addresses and city-only fallback.
- [x] 3.2 Add tests for missing-city behavior and source-boundary protection.
- [x] 3.3 Run focused extraction/context tests and the full suite in the conda `agent` environment.
