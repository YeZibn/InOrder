## 1. Evaluation dataset and model

- [x] 1.1 Define structured sample and per-strategy result models.
- [x] 1.2 Build 500 explicit positive, negative, short-confusion, and numeric-conflict samples.

## 2. Matcher implementations

- [x] 2.1 Implement RapidFuzz matcher with entity filtering, threshold, candidate gap, and dependency handling.
- [x] 2.2 Implement pure-Python character bigram/trigram matcher.
- [x] 2.3 Implement strict Ensemble requiring consistent candidates and passing business guards.

## 3. Evaluation and reporting

- [x] 3.1 Implement precision, false-positive rate, coverage, and abstain-rate metrics.
- [x] 3.2 Add reproducible report entrypoint comparing all strategies.
- [x] 3.3 Add regression tests proving experiment isolation and exact keyword behavior remains unchanged.

## 4. Verification

- [x] 4.1 Add matcher tests for variants, exclusions, short words, and numeric conflicts.
- [x] 4.2 Run the 500-case experiment and record results.
- [x] 4.3 Run the full test suite in the `agent` conda environment.

## 5. Production integration

- [x] 5.1 Add RapidFuzz to formal runtime dependencies and verify installation in `agent`.
- [x] 5.2 Add a production normalization adapter that preserves raw input and match metadata.
- [x] 5.3 Run exact keyword matching first, then invoke Ensemble only on exact misses; keep entity types isolated.
- [x] 5.4 Write only accepted canonical codes through the existing OrderContext reducer; rejected results must not overwrite context.
- [x] 5.5 Add integration tests for exact precedence, accepted variants, disagreement, short inputs, ranges, history, numeric conflicts, and mixed entity types.
- [x] 5.6 Run the 500-case regression report and full test suite; require zero false positives before enabling production path.
