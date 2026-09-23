## 1. Evaluate both range endpoints

- [x] 1.1 Run the existing weight, volume and packing checks independently with each vehicle's lower and upper capacity endpoints; do not skip cargo with missing required dimensions.

## 2. Classify and rank candidates

- [x] 2.1 Replace the ambiguous candidate `fit` boolean with `fit_level` values `lower_bound_fit` and `upper_bound_only`; rank lower-bound candidates first, prefer the smallest sufficient vehicle within each level, and return at most three candidates with upper-bound-only candidates filling open slots.

## 3. Preserve selection semantics

- [x] 3.1 Commit only a lower-bound estimated primary vehicle to `OrderContext`; keep upper-bound-only candidates as suggestions and preserve user-selected or existing canonical vehicles.

## 4. Explain the recommendation

- [x] 4.1 Propagate fit levels and concise boundary-based reasons through the structured result, order summary and CLI output.

## 5. Verify the behavior

- [x] 5.1 Add and run focused tests for lower-bound preference, upper-bound-only inclusion and ordering, the three-candidate limit, missing cargo dimensions, and context preservation; validate the OpenSpec change.
