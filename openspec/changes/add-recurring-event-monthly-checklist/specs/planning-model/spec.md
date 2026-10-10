## MODIFIED Requirements

### Requirement: Monthly approval workflow

`POST /api/v1/events/bulk-approval-status` SHALL change the approval status only for eligible slots of the requested district and month. A district-scoped `PLANNER` (or higher role) SHALL retain the existing district-wide approval permission; a request without `congregation_id` SHALL require this district-level permission. When a specific `congregation_id` is supplied, a `CONGREGATION_ADMIN` scoped to that congregation (or an authorized district-level actor) SHALL also be allowed to approve only that congregation's slots. The requested congregation SHALL belong to the district and authorization SHALL be enforced before reading or changing any planning slot. A congregation-scoped actor SHALL NOT approve district-level slots or another congregation's slots. Confirming a district-wide month SHALL publish a `PLAN_FINALIZED` domain event after commit; a congregation-scoped partial approval SHALL NOT publish this district-wide event. Existing prohibition of demoting previously released slots SHALL remain in force.

#### Scenario: Month confirmed for district

- **WHEN** a district-scoped `PLANNER` confirms a month without `congregation_id`
- **THEN** all eligible slots of that district and month are confirmed
- **AND** `PLAN_FINALIZED` is emitted after commit

#### Scenario: Congregation administrator approves own month's slots

- **GIVEN** a user holds only `CONGREGATION_ADMIN` for congregation A within district D
- **WHEN** they confirm a month with `district_id=D` and `congregation_id=A`
- **THEN** only congregation A's eligible slots in the selected month become `CONFIRMED`
- **AND** district-level slots, congregation B's slots, and other districts remain unchanged
- **AND** no district-wide `PLAN_FINALIZED` event is emitted

#### Scenario: Congregation administrator requests district-wide release

- **GIVEN** a user holds only `CONGREGATION_ADMIN` for congregation A
- **WHEN** they request monthly approval without `congregation_id`
- **THEN** the endpoint returns HTTP 403 and does not change any slots

#### Scenario: Congregation administrator requests another congregation

- **GIVEN** a user holds only `CONGREGATION_ADMIN` for congregation A
- **WHEN** they request approval with `congregation_id=B`
- **THEN** the endpoint returns HTTP 403 before reading or modifying congregation B's slots

#### Scenario: Forged or cross-district congregation ID

- **WHEN** a caller uses a `congregation_id` that does not belong to the selected district
- **THEN** the request is rejected without changing slots, regardless of the caller's membership in another district

#### Scenario: Previously confirmed slot cannot be demoted

- **WHEN** a caller attempts to set a previously released slot back to `PLANNED` using district-wide or congregation-scoped approval
- **THEN** the existing non-demotion rule rejects the operation without partial changes
