## 1. Event Contract

- [x] 1.1 Define typed workflow event names, payload models, and JSON/SSE frame serialization for `THINKING_START`, `THINKING_STEP`, `THINKING_DONE`, `CREATE_ORDER_CONTEXT`, `DONE`, and `ERROR`.
- [x] 1.2 Define safe stage metadata and error mappings so SSE payloads exclude prompts, raw LLM responses, hidden reasoning, and internal stack traces.

## 2. Graph Event Observation

- [x] 2.1 Add a parent-graph event observer or adapter that emits the start event and the intent-recognition stage without duplicating child graph nodes.
- [x] 2.2 Map order-subgraph execution boundaries to rewrite, extract, context update, optional cargo profile, optional vehicle resolution, and completion stages.
- [x] 2.3 Map the QA terminal branch to its shortened lifecycle and ensure it never emits an order-context event.
- [x] 2.4 Emit `CREATE_ORDER_CONTEXT` only when the order context has a persistable update, using the structured `OrderContext` snapshot.
- [x] 2.5 Preserve synchronous MainGraph `invoke` behavior, existing result keys, child graph independence, and existing exception propagation.

## 3. SSE HTTP API

- [x] 3.1 Add the `/api/v2/chat` request and response boundary with validation for `session_id`, non-empty `message`, optional history, optional order context, and optional reference time.
- [x] 3.2 Implement the SSE response generator with correct `text/event-stream` framing, event ordering, terminal `DONE`, and no post-terminal business events.
- [x] 3.3 Convert graph and LLM failures into one terminal `ERROR` event with a stable code, safe message, and stage metadata; do not emit `DONE` after errors.
- [x] 3.4 Detect client disconnects and stop publishing events while releasing request-scoped resources.
- [x] 3.5 Add a runnable local API entrypoint and document the conda `agent` startup command without changing the existing `inorder` CLI command.

## 4. Verification

- [x] 4.1 Add unit tests for event envelope serialization, stage payload allowlisting, error normalization, and terminal-event rules.
- [x] 4.2 Add graph tests covering order and QA event sequences, optional nodes, context update/no-update behavior, and preservation of existing synchronous results.
- [x] 4.3 Add API tests covering valid requests, validation failures, SSE headers/framing, disconnect handling, and upstream/child-graph failures.
- [x] 4.4 Run the focused SSE/API test suite and the existing graph/LLM test suite in the `agent` conda environment.
