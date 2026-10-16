# planning-model Specification

## Purpose

Defines the planning aggregate that replaced the legacy `events` table (dropped in Alembic revision 0125): `PlanningSlot` holds the planned structure, `EventInstance` the concrete (possibly externally synchronised) occurrence. Covers the events API, approval workflow, service marking, district-to-congregation distribution (UC-04), series and draft generation, and retention.

## Requirements

### Requirement: PlanningSlot and EventInstance separation
A `PlanningSlot` SHALL carry district, optional congregation and series, category, title, `planning_date`, `planning_time`, `status` (`ACTIVE` | `CANCELLED`), optional `approval_status` (`PLANNED` | `CONFIRMED`), invitation references and `applicability`. An `EventInstance` SHALL reference one slot and carry title, description, actual start/end, `source`, `visibility`, `deviation_flag` and sync metadata. There SHALL be no `events` table.

#### Scenario: Slot without an instance
- **WHEN** a slot has no `EventInstance`
- **THEN** APIs and exports derive the event view from the slot's date, time and title

### Requirement: No duplicate active congregation slots
The database SHALL reject a second `ACTIVE` planning slot for the same congregation, date and time; cancelled slots SHALL NOT block rescheduling onto that time.

#### Scenario: Duplicate active slot
- **WHEN** a second active slot is inserted for the same congregation, date and time
- **THEN** the unique index `no_overlapping_planning_slots` rejects it

### Requirement: Events API over planning slots
`GET /api/v1/events` SHALL list slots of a district for `VIEWER` (superadmins MAY omit `district_id`) with filters for congregation, group, district level, status, approval status, `is_service`, time range (default one year back to two years ahead) and pagination. `PATCH /api/v1/events/{id}` SHALL require `PLANNER`; a new congregation SHALL belong to the same district and the end SHALL NOT precede the start.

#### Scenario: Congregation from another district
- **WHEN** a planner moves an event to a congregation of another district
- **THEN** the API responds with 400

### Requirement: Service marking
Every event response SHALL contain `is_service`, true exactly when the category is `Gottesdienst`, and the list endpoint SHALL filter by it. The event list view SHALL offer a type filter and highlight services.

#### Scenario: Filter services
- **WHEN** `GET /api/v1/events?is_service=true` is called
- **THEN** only events with category `Gottesdienst` are returned

### Requirement: Event listing is bounded in the database
`GET /api/v1/events` SHALL reject a range whose `to_dt` precedes `from_dt` or that spans more than 1100 days with HTTP 422, and SHALL apply all filters, the total count and pagination in SQL so that at most one page of slots is materialised. Visibility rules SHALL be unchanged: a congregation sees its own slots in every state and district slots only while ACTIVE, CONFIRMED and applicable to it.

#### Scenario: Oversized or reversed range
- **WHEN** the requested range exceeds 1100 days or ends before it starts
- **THEN** the response is HTTP 422 and no slots are queried

#### Scenario: Pagination with filters
- **WHEN** a filtered list is requested with `limit` and `offset`
- **THEN** `total` counts all matching slots and the items are the requested page in stable order

### Requirement: Monthly approval workflow

`POST /api/v1/events/bulk-approval-status` SHALL change the approval status only for eligible slots of the requested district and month. A district-scoped `PLANNER` (or higher role) SHALL retain the existing district-wide approval permission; a request without `congregation_id` SHALL require this district-level permission. A congregation-scoped actor SHALL NOT approve district-level slots or another congregation's slots.

#### Scenario: Additional constraints for Monthly approval workflow
- **GIVEN** this requirement is applicable
- **WHEN** the system processes the relevant operation
- **THEN** When a specific `congregation_id` is supplied, a `CONGREGATION_ADMIN` scoped to that congregation (or an authorized district-level actor) SHALL also be allowed to approve only that congregation's slots. The requested congregation SHALL belong to the district and authorization SHALL be enforced before reading or changing any planning slot. Confirming a district-wide month SHALL publish a `PLAN_FINALIZED` domain event after commit; a congregation-scoped partial approval SHALL NOT publish this district-wide event. Existing prohibition of demoting previously released slots SHALL remain in force.

#### Scenario: Month confirmed

- **WHEN** a planner sets a month to `CONFIRMED`
- **THEN** all slots of that month are confirmed and `PLAN_FINALIZED` is emitted

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

### Requirement: District event distribution
A district-level slot SHALL be distributable via `applicability` holding either the sentinel `all` alone or congregation IDs of the same district, stored canonically without duplicates; congregation-level slots SHALL never be distributed. A congregation view SHALL include its own slots plus `ACTIVE` district slots distributed to it, without copying data.

#### Scenario: Distributed to all congregations
- **WHEN** a district slot has `applicability = ["all"]` and is active
- **THEN** it appears in the event list of every congregation of the district

#### Scenario: Ambiguous distribution
- **WHEN** `applicability` contains `all` and a congregation ID
- **THEN** the API responds with 400 and the previous distribution is kept

### Requirement: Planning series generation
Planning series SHALL describe recurring slots (weekdays pattern, default time, optional congregation and category, active range). `POST /api/v1/planning-series`, `PATCH`, and the generate endpoints SHALL require `DISTRICT_ADMIN`; reading SHALL require `VIEWER`. The beat task `generate_planning_series_slots` SHALL run daily at 01:20 with a 12-month horizon.

#### Scenario: Series generation
- **WHEN** slots are generated for an active series
- **THEN** missing slots on matching weekdays within the horizon are created

#### Scenario: Previously generated series occurrence is moved
- **WHEN** a generated PlanningSlot is moved to another date without changing its series scope
- **THEN** its stable generation key identifies the original occurrence
- **AND** neither the background generator nor the API generator inserts a duplicate at the former date

### Requirement: Draft service generation
Draft `Gottesdienst` slots with a public `EventInstance` and without assignment SHALL be generated from each congregation's `service_times` for an 8-week rolling horizon, daily at 01:10 via `generate_draft_services_window` and on demand via `POST /api/v1/districts/{id}/matrix/generate-drafts` (`PLANNER`). A run SHALL skip congregation date/time combinations that already have a `Gottesdienst` slot.

#### Scenario: Repeated generation
- **WHEN** generation runs twice for the same window
- **THEN** the second run creates no additional slots

### Requirement: Retention cleanup
The beat task `cleanup_old_events` SHALL delete planning slots whose `planning_date` is older than 24 months on the first day of each month and SHALL record one bulk-delete audit entry.

#### Scenario: Old slots removed
- **WHEN** the cleanup runs
- **THEN** slots older than the cutoff and their dependent rows are removed and an audit row with reason `retention` exists
