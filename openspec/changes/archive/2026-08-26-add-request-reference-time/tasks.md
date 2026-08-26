## 1. Request Boundary and Time Utilities

- [x] 1.1 Add shared Asia/Shanghai reference-time generation and format validation for caller-provided values.
- [x] 1.2 Ensure HTTP requests resolve one non-empty reference_time before constructing Graph State, preserving valid caller input.
- [x] 1.3 Move CLI reference-time resolution from session initialization to the start of each user-message handling cycle.

## 2. Workflow Propagation

- [x] 2.1 Propagate the resolved reference_time through MainGraph and OrderProcessingGraph state without storing it in OrderContext.
- [x] 2.2 Pass the same reference_time to Rewrite and Extract boundaries, including structured-output repair retries.
- [x] 2.3 Reject invalid reference-time input with a stable validation error before starting the workflow.

## 3. Verification and Documentation

- [x] 3.1 Add tests for caller-provided, default-generated, invalid, and per-message CLI reference times.
- [x] 3.2 Add tests proving Rewrite/Extract and retry paths reuse one reference_time value.
- [x] 3.3 Update README and relevant API/CLI documentation with the request-level reference-time contract.
