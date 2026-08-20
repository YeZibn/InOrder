## 1. Catalog-driven extraction contract

- [x] 1.1 Add a catalog rendering helper that exposes vehicle labels, aliases, categories, and specs for prompt vocabulary without duplicating canonical data.
- [x] 1.2 Update the LangExtract order prompt to use catalog vocabulary for classification and splitting while requiring raw vehicle expressions instead of canonical codes.
- [x] 1.3 Update LangExtract few-shot examples for exact aliases, combined vehicle/spec expressions, ambiguous expressions, and length ranges.

## 2. Adapter and entity behavior

- [x] 2.1 Ensure grounded vehicle entities preserve source `extraction_text` and optional raw attributes without adapter-side code conversion or semantic repair.
- [x] 2.2 Add validation coverage proving that vehicle types and specs remain separate entities and that ambiguous/range expressions are not forced to a single code.
- [x] 2.3 Reconcile the extract-to-context boundary so unnormalized vehicle expressions are not silently treated as canonical vehicle codes.

## 3. Verification and documentation

- [x] 3.1 Update existing extraction and catalog tests to assert source preservation, catalog-driven prompt content, and removal of direct code-generation requirements.
- [x] 3.2 Run the full test suite in the `agent` conda environment and resolve regressions in order processing tests.
- [x] 3.3 Document that canonical vehicle normalization, fuzzy matching, range handling, and vehicle recommendation are deferred to a separate change.
