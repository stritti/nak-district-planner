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

### Requirement: Monthly approval workflow
`POST /api/v1/events/bulk-approval-status` SHALL set the approval status of all slots of a district in a given month for a `PLANNER`. Confirming a month SHALL publish a `PLAN_FINALIZED` domain event after commit.

#### Scenario: Month confirmed
- **WHEN** a planner sets a month to `CONFIRMED`
- **THEN** all slots of that month are confirmed and `PLAN_FINALIZED` is emitted

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
