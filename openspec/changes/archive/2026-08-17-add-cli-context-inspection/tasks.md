## 1. Assistant History Summary

- [x] 1.1 Add a structured summary builder for intent, order, full, and clarification results.
- [x] 1.2 Append only the concise assistant summary after successful ordinary-message processing.
- [x] 1.3 Preserve failure behavior: do not append assistant summaries when graph or reducer execution raises.
- [x] 1.4 Add metadata fields for chain, intent, entity count, and context update status without storing raw payloads.

## 2. CLI Inspection Commands

- [x] 2.1 Add `/context` and `/conversation` command handling with JSON output.
- [x] 2.2 Ensure inspection commands are read-only and do not call graphs or modify session state.
- [x] 2.3 Update help text and README command documentation.

## 3. Verification

- [x] 3.1 Test concise assistant history content and exclusion of debug/entity/context payloads.
- [x] 3.2 Test failed graph execution does not append an assistant turn.
- [x] 3.3 Test `/context` and `/conversation` output for empty and populated sessions.
- [x] 3.4 Run the full test suite in conda `agent`.
