## 1. Error and Retry Model

- [x] 1.1 Add typed retry/timeout errors and stable error metadata including stage and `retryable`.
- [x] 1.2 Refine LLM transport retry classification, exponential backoff cap, and per-call timeout configuration.
- [x] 1.3 Add one-time structured-output repair retry at resolver boundaries.

## 2. Workflow Policy

- [x] 2.1 Add a per-request workflow deadline and prevent starting nodes after budget exhaustion.
- [x] 2.2 Keep node retry disabled by default and provide an explicit limited policy for transient node dependencies.
- [x] 2.3 Emit normalized timeout/retryable errors through SSE without exposing internal retry attempts.

## 3. Verification

- [x] 3.1 Add unit tests for transport retry, fatal errors, format repair, and retry caps.
- [x] 3.2 Add workflow/API tests for deadline exhaustion, disconnect behavior, and error payloads.
- [x] 3.3 Run the focused retry/SSE suite and the existing full suite in conda `agent`.
