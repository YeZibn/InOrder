## 1. LangExtract Prompt Contract

- [x] 1.1 Define the complete LangExtract prompt description and source formatting in `extract/resolver.py`, including grounded source boundaries, action rules, 14 entity contracts, remark representation, and empty extraction behavior.
- [x] 1.2 Define resolver-owned schema-covering LangExtract examples for all 14 entity classes and every supported attribute, including vehicle catalog codes and nullable optional fields.
- [x] 1.3 Update the LangExtract adapter to consume resolver-owned prompt definitions without adding semantic inference.

## 2. Extraction Input Boundary

- [x] 2.1 Change the extractor protocol and ExtractNode so extraction receives only rewrite extraction text and reference time.
- [x] 2.2 Update the LangExtract source construction and JSON fallback extractor to use the same two-input boundary while leaving history and OrderContext in rewrite.

## 3. Verification

- [x] 3.1 Add unit tests proving the generated schema covers all 14 classes and their required attributes, and that adapter mapping preserves LLM-decided semantics.
- [x] 3.2 Add order-subgraph tests proving history and OrderContext are consumed by rewrite but not passed into extract.
- [x] 3.3 Add focused prompt contract cases for action variants, vehicle combinations, time, contacts, enum entities, grounded remarks, and empty extraction.
- [x] 3.4 Run opt-in live LangExtract probes against the configured gateway and assert grounded basic order, vehicle/spec, and remark behavior.

## 4. Documentation and Regression

- [x] 4.1 Update `PROMPT_CHANGELOG.md` and README with the complete prompt contract and extract input boundary.
- [x] 4.2 Run focused tests and the complete test suite in conda `agent`.
