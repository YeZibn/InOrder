## 1. Order Graph Context Update

- [x] 1.1 Extend order graph state and node wiring with a post-extract context update stage.
- [x] 1.2 Apply `OrderContextReducer` to extracted entities without mutating the input context.
- [x] 1.3 Preserve the original context on clarification and ensure reducer/normalization failures abort without partial results.
- [x] 1.4 Return updated `order_context` and `order_context_updated` alongside existing rewrite, entity, and clarification fields.

## 2. CLI Runner and Session Integration

- [x] 2.1 Propagate the order graph's returned context and update status through `OrderChainRunner`.
- [x] 2.2 Write the returned context back to the active `CliSession` for order and full chains only after successful graph execution.
- [x] 2.3 Add context update status to order/full CLI output while preserving existing parsing-stage output.

## 3. Verification

- [x] 3.1 Add graph tests for set/add/replace/remove multi-turn context updates and input immutability.
- [x] 3.2 Add clarification and reducer failure tests proving context is not updated.
- [x] 3.3 Add CLI tests proving order/full chains persist updated context across consecutive messages.
- [x] 3.4 Run the full test suite in the conda `agent` environment.
