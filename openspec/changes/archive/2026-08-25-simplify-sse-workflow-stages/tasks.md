## 1. Event Mapping

- [x] 1.1 Restrict public `THINKING_STEP` stages to intent, order, cargo profile, and vehicle.
- [x] 1.2 Aggregate rewrite, extract, and context update into the order stage.
- [x] 1.3 Preserve context, done, and error event behavior.

## 2. Verification

- [x] 2.1 Update SSE adapter tests for order and QA event sequences.
- [x] 2.2 Add regression assertions that internal node names are not emitted.
- [x] 2.3 Run focused SSE tests and the existing full test suite in conda `agent`.
