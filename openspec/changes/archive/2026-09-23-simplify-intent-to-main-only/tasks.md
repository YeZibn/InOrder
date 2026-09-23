## 1. Intent model and prompt

- [x] 1.1 Simplify intent prompt and parser to return only `main_intent` and `confidence`.
- [x] 1.2 Remove `IntentStep`, sub-intent protocol methods, dependency validation, and obsolete exports.

## 2. Graph and integration

- [x] 2.1 Remove SubIntentNode and simplify intent graph/state to main-intent classification and finalization.
- [x] 2.2 Update parent graph, CLI, API/SSE adapters, and serializers to stop emitting or displaying sub-intents.
- [x] 2.3 Keep order completeness checks and entity-action processing as the source of clarification and order mutation.

## 3. Tests and verification

- [x] 3.1 Update intent graph/model/CLI tests for main-only output and no sub-intent LLM call.
- [x] 3.2 Add mixed execution/consultation and confidence validation cases.
- [x] 3.3 Validate the original main-only implementation and its initial OpenSpec artifacts.

## 4. Close out the main-only intent refactor

- [x] 4.1 Remove obsolete `sub_intent`, `build_plan`, and `validate_plan` entries from the workflow event adapter; remove the unused intent routing import and `graph/intent/routing.py` module.
- [x] 4.2 Rewrite the stale README intent-planning section and update `SYSTEM_GAPS.md` to reflect the implemented MainGraph and the still-missing real QA capability.
- [x] 4.3 Make `FullChainRunner` delegate only to MainGraph; return a clear configuration-unavailable result when `full` has no MainGraph, while preserving standalone `intent` and `order` chains.
- [x] 4.4 Correct CLI formatting for MainGraph QA terminal results and add focused coverage for QA display, order routing, and missing-MainGraph behavior.
- [x] 4.5 Search active code and user-facing docs for stale architecture claims, run the relevant CLI/workflow tests and full test suite, then validate this OpenSpec change.
