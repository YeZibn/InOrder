## 1. Cargo shape and reduction

- [x] 1.1 Update the cargo data shape so each cargo item stores `weight`, `quantity`, `volume`, and `dimensions` as raw value lists.
- [x] 1.2 Adjust cargo reduction so `set` and `replace` overwrite the current raw lists, while `add` appends only non-empty raw values.
- [x] 1.3 Treat omitted, `null`, empty-string, and empty-list cargo attributes as absent input and keep them out of stored lists.

## 2. Compatibility and persistence

- [x] 2.1 Preserve backward compatibility when existing cargo records still contain scalar strings by reading them as single raw values.
- [x] 2.2 Keep JSON serialization stable for sessions and CLI context output after cargo attributes become lists.
- [x] 2.3 Preserve cargo removal behavior so `remove` deletes the whole cargo record identified by name.

## 3. Verification

- [x] 3.1 Add reducer tests for cargo `set`, `add`, `replace`, and `remove` with raw list storage.
- [x] 3.2 Add tests verifying that `null` and other empty cargo attributes are ignored without reduction errors.
- [x] 3.3 Add graph or CLI-level coverage showing repeated cargo additions preserve raw expressions instead of calculating totals.
