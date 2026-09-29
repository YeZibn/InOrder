## 1. Unify entity normalization and order-state updates

- [x] 1.1 Clarify `OrderGraphState` field ownership in its type/docs: one working `OrderContext`, current-turn entities, request inputs, derived results, and control flags.
- [x] 1.2 Add one normalization graph node after Extract that dispatches the existing time, phone, enum, vehicle-type, and vehicle-spec rules; pass through other entity types and preserve raw expressions, actions, and match status.
- [x] 1.3 Change the reducer contract to consume already-normalized entities and apply actions without calling normalizers or repeating alias/fuzzy catalog matching; make vehicle processing consume the same normalized entity list.
- [x] 1.4 Verify context reduction precedes cargo-profile and vehicle processing, and that completeness reads the final working context plus current-turn vehicle result.
- [x] 1.5 Add regression tests for input-context immutability, cargo changes reaching profile/vehicle processing, and unresolved vehicle source text/action surviving normalization.
- [x] 1.6 Verify strict time, phone, and enum normalization errors fail before context reduction, while unmatched vehicle expressions remain available to the existing vehicle decision path.
- [x] 1.7 Migrate every direct `OrderContextReducer.apply` caller and its tests to normalize entities explicitly before reduction; verify no hidden normalization remains inside the reducer.

## 2. Unify result projection and session commit

- [x] 2.1 Add a caller-facing MainGraph output projection that returns `order_context` only inside `order_result` and omits `order_result` on the QA route.
- [x] 2.2 Wrap standalone OrderChainRunner output under `order_result` and keep its order-result fields aligned with the full-chain runner.
- [x] 2.3 Update CLI formatting, summaries, and session updates to read only `order_result.order_context`; preserve the prior context when the runner fails or returns no completed order result.
- [x] 2.4 Update workflow result adaptation to consume the single nested context path while preserving existing SSE event types, payload semantics, and ordering.
- [x] 2.5 Add contract tests for standalone order, full order, full QA, and SSE results, including absence of a duplicate root-level context and no new public normalization progress event.

## 3. Validate the change

- [x] 3.1 Run focused graph, reducer, runner, CLI, and workflow tests for the changed contracts.
- [x] 3.2 Run the full test suite and strict OpenSpec validation; resolve any failures caused by this change.
- [x] 3.3 Run `git diff --check` and verify no caller still reads the removed root-level order context or flat standalone order result.
