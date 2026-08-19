## 1. LangExtract Backend and Models

- [x] 1.1 Add a pinned `langextract` dependency and model/provider configuration compatible with the existing LLM gateway.
- [x] 1.2 Add grounded extraction models with extraction class, source text, attributes, and optional alignment metadata.
- [x] 1.3 Implement an injectable LangExtract adapter that receives message, history, and reference time.

## 2. Business Mapping and Validation

- [x] 2.1 Implement mapper from grounded extractions to reducer-compatible entities, storing action in attributes and preserving source text.
- [x] 2.2 Implement current simple-order rules for cargo, pickup/dropoff locations, vehicle type/specs, and action defaults.
- [x] 2.3 Add explicit-order-signal detection and raise a clear extraction error when grounded output is empty for an explicit order request.
- [x] 2.4 Preserve empty results for non-order text and preserve structured failure behavior.

## 3. Graph and Compatibility Integration

- [x] 3.1 Keep `EntityExtractorModel` and `ExtractNode` boundaries stable while wiring the new extractor implementation.
- [x] 3.2 Adapt `OrderContextReducer` input handling to read action from mapped entity attributes without changing reducer semantics.
- [x] 3.3 Update extraction prompt/examples or LangExtract examples and document the new extraction contract.

## 4. Verification and Migration

- [x] 4.1 Add unit tests for grounded model mapping, action attributes, source spans, location roles, and empty extraction errors.
- [x] 4.2 Add an opt-in live LangExtract probe for “一吨苹果从温州到上海” asserting non-empty grounded entities.
- [x] 4.3 Keep compatibility tests for order graph and context updates.
- [x] 4.4 Run the full test suite in conda `agent` and document rollback/configuration.

## 5. Remove Local Semantic Decisions

- [x] 5.1 Remove keyword/regex-based explicit-order detection and preserve empty LangExtract results unchanged.
- [x] 5.2 Remove mapper inference for action, location role, city, cargo fields, and vehicle semantics; retain only compatibility copying and output-contract validation.
- [x] 5.3 Update LangExtract prompt/examples and tests so semantic fields are asserted as LLM-provided values rather than mapper defaults.
- [x] 5.4 Update prompt changelog and run focused, live opt-in, and full conda `agent` test suites.
