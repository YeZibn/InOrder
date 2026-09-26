## ADDED Requirements

### Requirement: Maintain current vehicle provenance

`OrderContext.vehicle_type` SHALL contain only the current effective canonical vehicle type. When it is present, `vehicle_source` SHALL be `user_matched` or `estimated`; when no effective canonical vehicle exists, both fields SHALL be empty. `user_matched` SHALL be set only when an explicit user `vehicle_type` expression successfully matches the vehicle catalog. `vehicle_specs` SHALL retain user-provided vehicle constraints and SHALL NOT determine or change the source of `vehicle_type`. Cargo-derived vehicle specifications SHALL remain in the current resolution result and SHALL NOT be persisted as user-provided context.

#### Scenario: Add a user vehicle specification to an estimated vehicle
- **WHEN** the current context has `vehicle_type=truck_5m2` and `vehicle_source=estimated`, and the user adds the matched `cold_chain` specification without selecting a vehicle type
- **THEN** the system SHALL retain `vehicle_type=truck_5m2` and `vehicle_source=estimated`, and SHALL add `cold_chain` to user-provided `vehicle_specs`

#### Scenario: Keep cargo-derived specifications out of user context
- **WHEN** cargo profiles imply a required vehicle specification and estimation returns it with a candidate
- **THEN** the system SHALL include the specification in the vehicle resolution result and SHALL NOT add it to `OrderContext.vehicle_specs` unless the user provided it

#### Scenario: Clear source when no effective vehicle remains
- **WHEN** vehicle resolution has no lower-bound primary vehicle and no matched user vehicle remains
- **THEN** the system SHALL set `OrderContext.vehicle_type` and `OrderContext.vehicle_source` to empty values

## MODIFIED Requirements

### Requirement: Prefer a matched user vehicle

The system SHALL first match explicit user vehicle expressions against the vehicle catalog. When a user-provided `vehicle_type` matches, the system SHALL adopt its canonical type, retain any user-provided specifications, and mark the effective context and resolution source as `user_matched`. While a matched user vehicle remains active, the system SHALL preserve it across cargo, pickup-city, and vehicle-specification changes; it SHALL NOT perform cargo-fit estimation or replace the selected type based on those changes. A later successfully matched explicit user vehicle SHALL replace the previous active type.

#### Scenario: Resolve an exact user vehicle
- **WHEN** the user inputs “用4米2厢式车” and the vehicle expression matches the catalog
- **THEN** the system SHALL use `vehicle_type=truck_4m2`, retain the matched user specification `enclosed`, and report `source="user_matched"`

#### Scenario: Keep a matched vehicle despite cargo changes
- **WHEN** the current context has a matched user vehicle and the user adds, removes, or changes cargo quantities or dimensions
- **THEN** the system SHALL retain the matched user vehicle without invoking cargo-fit estimation or automatically replacing it

#### Scenario: Keep a matched vehicle despite pickup-city or specification changes
- **WHEN** the current context has a matched user vehicle and the pickup city or user-provided vehicle specifications change
- **THEN** the system SHALL retain the matched user vehicle without cargo-fit estimation or automatic replacement

#### Scenario: Replace the active vehicle with a newly matched user vehicle
- **WHEN** the current active vehicle is estimated or user-matched and the user explicitly replaces it with a catalog-matched vehicle
- **THEN** the system SHALL store the new canonical vehicle type and set its source to `user_matched`

### Requirement: Estimate when no usable user vehicle exists

When no matched user vehicle is active, the system SHALL estimate from the current cargo profiles, cargo summary, and effective city, and SHALL retain current user-provided vehicle specifications in the resolution result. It SHALL return at most three candidates, using the existing deterministic vehicle-capability calculation and ordering. Candidates passing all capability lower-bound checks SHALL be marked `lower_bound_fit`; candidates passing only upper-bound checks SHALL be marked `upper_bound_only` and ordered after lower-bound candidates. Only a `lower_bound_fit` candidate SHALL become the estimated primary vehicle. This change SHALL NOT introduce vehicle-type/specification compatibility rules absent from the catalog. When an active estimated vehicle's cargo profiles, effective pickup city, or user-provided vehicle specifications change, the system SHALL resolve again using the current inputs. If resolution produces no lower-bound primary vehicle, the system SHALL clear the previous estimated `vehicle_type` and `vehicle_source` while retaining any candidates and explanation in the resolution result. The effective city SHALL prefer the order pickup city, then the caller's user-location city, then the national default catalog.

#### Scenario: Estimate without a vehicle expression
- **WHEN** the user provides cargo information and there is no active matched user vehicle
- **THEN** the system SHALL estimate from the current cargo profiles and return at most three candidates with lower-bound candidates before upper-bound-only candidates

#### Scenario: Include upper-bound-only recommendations
- **WHEN** a vehicle fails lower-bound checks but passes upper-bound checks
- **THEN** the system SHALL return it as an `upper_bound_only` candidate after all lower-bound candidates

#### Scenario: Do not promote an upper-bound-only candidate
- **WHEN** there is no `lower_bound_fit` candidate but one or more `upper_bound_only` candidates exist
- **THEN** the resolution result SHALL retain the candidates but SHALL have no primary vehicle, and the context SHALL have no active estimated vehicle

#### Scenario: Recompute an estimate after cargo changes
- **WHEN** the active vehicle source is `estimated` and the user changes cargo so that its profiles or summary change
- **THEN** the system SHALL recompute using the updated cargo snapshot and replace the old estimate only with a new lower-bound primary vehicle

#### Scenario: Refresh an estimate after pickup city or user specifications change
- **WHEN** the active vehicle source is `estimated` and the effective pickup city or user-provided vehicle specifications change
- **THEN** the system SHALL resolve using the updated city and SHALL include the current user-provided specifications in the resolution result

#### Scenario: Clear an estimate when recomputation finds no primary vehicle
- **WHEN** the active vehicle source is `estimated` and a dependency change produces no lower-bound primary vehicle
- **THEN** the system SHALL clear the old context vehicle type and source while returning any upper-bound candidates and the reason for the result

#### Scenario: Fall back from an unmatched expression when no user vehicle remains
- **WHEN** a vehicle expression cannot be uniquely matched and no matched user vehicle remains active
- **THEN** the system SHALL keep the raw expression in the resolution result and use deterministic estimation without writing that expression as a canonical value

#### Scenario: Estimate with pickup city catalog
- **WHEN** no matched user vehicle is active and the order pickup city is 温州
- **THEN** the system SHALL use the 温州 catalog for vehicle estimation

#### Scenario: Fall back to user location
- **WHEN** the order pickup city is absent and the caller's user-location city is 上海
- **THEN** the system SHALL use the 上海 catalog for vehicle estimation

#### Scenario: Fall back to global data
- **WHEN** neither the pickup city nor user-location city selects a covered city catalog
- **THEN** the system SHALL use the national default catalog for vehicle estimation

### Requirement: Preserve unresolved vehicle input

An unmatched vehicle expression SHALL remain available as raw input in the resolution result or diagnostics and SHALL NOT be written into `OrderContext.vehicle_type` or `vehicle_specs` as a canonical value. An unmatched expression without explicit replacement intent SHALL NOT clear or overwrite an existing canonical vehicle. An explicit `replace` action with an unmatched new vehicle expression SHALL invalidate the previous active vehicle, clear its type and source, retain the raw expression, and proceed to estimation. An explicit vehicle `remove` action SHALL clear the active type and source and proceed to estimation while preserving independent user vehicle specifications.

#### Scenario: Preserve a user vehicle for a non-replacement question
- **WHEN** the current context has user-matched `truck_4m2` and the user asks whether a “大车” might be suitable without expressing replacement intent
- **THEN** the system SHALL retain `truck_4m2` and SHALL NOT treat “大车” as a canonical type or replace the user's selection

#### Scenario: Invalidate the old vehicle for an unmatched explicit replacement
- **WHEN** the current context has an active vehicle and the user explicitly says “换成大车”, but “大车” cannot be uniquely matched
- **THEN** the system SHALL clear the previous active vehicle and source, retain “大车” as raw input, and proceed to deterministic estimation

#### Scenario: Remove a selected vehicle and estimate from remaining constraints
- **WHEN** the user explicitly removes the vehicle selection
- **THEN** the system SHALL clear the active vehicle type and source, retain remaining user vehicle specifications, and proceed to deterministic estimation
