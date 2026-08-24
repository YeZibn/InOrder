## 1. Configurable transport

- [x] 1.1 Add a configurable transport mode and support Chat Completions and Responses request mapping.
- [x] 1.2 Normalize both response shapes into the existing `LLMResponse` contract.
- [x] 1.3 Select the endpoint from `LLM_API_MODE`, defaulting to `chat_completions`.

## 2. LangExtract integration

- [x] 2.1 Keep a LangExtract Responses provider and use the built-in Chat Completions provider when configured.
- [x] 2.2 Preserve structured extraction parsing, grounding, alignment metadata and reasoning effort forwarding for both modes.
- [x] 2.3 Ensure extractor endpoint selection follows `LLM_API_MODE`.

## 3. Configuration and user-facing behavior

- [x] 3.1 Keep `LLM_BASE_URL` as the `/v1` service root and document `LLM_API_MODE` endpoint behavior.
- [x] 3.2 Update README, command help and environment examples for both modes.
- [x] 3.3 Keep raw LLM content callback output working for CLI diagnostics.

## 4. Tests and verification

- [x] 4.1 Update transport/client fixtures to model Responses API request and response shapes.
- [x] 4.2 Add tests asserting mode-specific calls and normalization of both response shapes.
- [x] 4.3 Add LangExtract adapter tests for Responses provider success, malformed output and upstream failures.
- [x] 4.4 Run the full suite in conda `agent` and run opt-in live gateway probes when configured.
