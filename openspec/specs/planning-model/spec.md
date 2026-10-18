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
`GET /api/v1/events` SHALL list slots of a district for `VIEWER` (superadmins MAY omit `district_id`) with filters for congregation, group, district level, status, approval status, `is_service`, time range and pagination. `PATCH`, `POST` and `DELETE` on `/api/v1/events` SHALL require `PLANNER` in the relevant district. Creation SHALL save a `PlanningSlot` and `EventInstance` atomically, and creation and updates SHALL reject foreign-district congregations and invalid time ranges.

#### Scenario: Default time range
- **WHEN** no `from_dt` and `to_dt` are given
- **THEN** the list covers one year back to two years ahead

#### Scenario: Deleted event
- **WHEN** an event was deleted manually
- **THEN** it is absent from subsequent event listings

#### Scenario: New draft event
- **WHEN** a planner creates a valid event with start, end and title
- **THEN** the server returns 201, saves an `ACTIVE` slot with approval `PLANNED` and an INTERNAL-sourced instance, and returns its stable ID

#### Scenario: Invalid event
- **WHEN** a planner provides an end earlier than or equal to start, an unrecognized congregation or an invalid distribution
- **THEN** the server rejects the request without saving an event

#### Scenario: Congregation from another district
- **WHEN** a planner moves an event to a congregation of another district
- **THEN** the API responds with 400

### Requirement: Service marking
Every event response SHALL contain `is_service`, true exactly when the category is `Gottesdienst`, and the list endpoint SHALL filter by it. The event list view SHALL offer a type filter and highlight services.

#### Scenario: Filter services
- **WHEN** `GET /api/v1/events?is_service=true` is called
- **THEN** only events with category `Gottesdienst` are returned

### Requirement: Event listing is bounded in the database
`GET /api/v1/events` SHALL bound a request before querying: invalid or oversized ranges and offsets are rejected, and filters, total and pagination run in SQL so at most one page of slots is materialised. Visibility rules SHALL be unchanged: a congregation sees its own slots in every state and district slots only while ACTIVE, CONFIRMED and applicable to it.

#### Scenario: Oversized or reversed range
- **WHEN** the requested range exceeds 1100 days or ends before it starts
- **THEN** the response is HTTP 422 and no slots are queried

#### Scenario: Deep pagination
- **WHEN** `offset` exceeds 10000
- **THEN** the response is HTTP 422

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
The beat task `cleanup_old_events` SHALL delete only never-released planning slots whose `planning_date` is older than 24 months on the first day of each month and SHALL record one bulk-delete audit entry. Previously released events (including cancelled events) SHALL NOT be permanently removed by retention. Retention SHALL use the relationship-aware PlanningSlot repository deletion to clear invitation links, delete unreleased target copies, and retain released target copies as cancellations.

#### Scenario: Old slots removed
- **WHEN** the cleanup runs with never-released slots older than the cutoff
- **THEN** those slots and their dependent unreleased rows are removed and a bulk audit entry with reason `retention` exists, while previously released records are preserved

#### Scenario: Old unreleased slots removed
- **WHEN** the cleanup runs
- **THEN** never-released slots older than the cutoff and their dependent rows are removed and an audit row with reason `retention` exists

#### Scenario: Retention of an invited draft
- **WHEN** a never-released invitation source passes the retention cutoff
- **THEN** its invitations and unpublished target copies are removed and any released target copy survives as `CANCELLED`

#### Scenario: Old released slots retained
- **WHEN** the cleanup runs and older released or cancelled events exist
- **THEN** the released event identities and their dependent occurrences remain intact

### Requirement: Irreversible event publication boundary

The first release of a slot SHALL persist its `released_at` and stable identity. A previously released slot SHALL NOT be hard-deleted or reverted to `PLANNED`; cancellation is permitted. All concurrent update, delete and invitation operations MUST protect this boundary with refreshed row state and a consistent district-scoped transaction lock.

#### Scenario: Draft deleted
- **WHEN** a planner deletes an event that has never been confirmed
- **THEN** the slot and its dependent occurrences are deleted; generated slots first persist their generation key in a separate suppression ledger; the endpoint returns 204

#### Scenario: Released event deletion blocked
- **WHEN** deletion of a current or formerly confirmed event is requested
- **THEN** the endpoint returns 409 and the event remains available for cancellation exports

#### Scenario: Attempt to withdraw publication
- **WHEN** a single or bulk approval request attempts to return a released event to `PLANNED`
- **THEN** it returns 409 without applying the downgrade

#### Scenario: Concurrent source and linked target deletion
- **WHEN** planners delete an invitation source and target simultaneously
- **THEN** both deletions acquire the same district lock before individual slot and invitation locks, avoiding deadlocks

#### Scenario: Concurrent deletion during event update
- **WHEN** a PATCH or monthly bulk approval update loaded a draft that another transaction subsequently deleted
- **THEN** the update returns HTTP 409, never recreates the event, and publishes no partially applied monthly result

#### Scenario: Concurrent release during invitation removal
- **WHEN** an invitation target becomes released while the invitation removal starts
- **THEN** the locked latest target is cancelled rather than deleted and the invitation is removed without HTTP 500

#### Scenario: Invitation source deletion
- **WHEN** a planner deletes an unreleased invitation source event
- **THEN** its invitations and unreleased target copies disappear, but released target copies retain their identity and become `CANCELLED`

#### Scenario: Invitation target deletion
- **WHEN** a planner deletes an unreleased invited target event
- **THEN** the corresponding invitation is removed without deleting its source event

#### Scenario: Concurrent update after release
- **WHEN** an outdated draft update races with another request confirming the same slot
- **THEN** the persisted release is protected under a row lock, the stale downgrade is rejected, and PATCH returns HTTP 409 instead of 500

#### Scenario: Concurrent monthly publication update
- **WHEN** a bulk approval request reads an unpublished slot and another transaction publishes or cancels it before the repository save
- **THEN** the request receives HTTP 409 rather than 500 and the transaction does not publish a partial monthly result

#### Scenario: Retention of released cancellations
- **WHEN** the monthly retention job runs and an event was previously released
- **THEN** that event remains available even when its planned date is older than the retention cutoff

#### Scenario: Provider hard delete after release
- **WHEN** a linked provider removes a released event configured for `HARD_DELETE`
- **THEN** the slot survives with `CANCELLED` status and the original event identity

#### Scenario: Generated draft deleted
- **WHEN** a planner deletes a generated draft that has a generation key
- **THEN** it is deleted from the events table and exports, its generator key is kept in a district-scoped deletion ledger, and it is not regenerated by the next nightly generation run

### Requirement: Persist manual deletion of generated draft occurrences

Deleting an unreleased generated slot SHALL persist a tenant-scoped suppression marker instead of recreating the slot. Both draft and planning-series generators MUST respect suppression, handle concurrent generation idempotently, and use a consistent district transaction lock. Detached occurrences MUST NOT suppress their original generation key.

#### Scenario: Deleted generated Gottesdienst
- **WHEN** a planner deletes an autogenerated unreleased Gottesdienst and the draft generator runs again
- **THEN** the removed slot is not recreated

#### Scenario: Concurrent series generation
- **WHEN** two schedulers attempt to insert the same recurring occurrence
- **THEN** only one slot is stored and the second attempt is skipped without an orphan instance or aborted batch

#### Scenario: Concurrent explicit series generation
- **WHEN** two manual or background requests generate the same planning-series occurrence concurrently
- **THEN** the second insert is counted as skipped without an uncaught unique constraint exception, and other slots from the run remain created

#### Scenario: Concurrent deletion between generator reads
- **WHEN** deletion of a series occurrence commits between an existing-slot read and a tombstone read
- **THEN** the generator observes its deletion marker and does not regenerate the occurrence

#### Scenario: Detached legacy series occurrence
- **WHEN** an occurrence is reassigned to another congregation or category
- **THEN** neither generator treats its detached slot as the original occurrence

#### Scenario: Reassigned series occurrence deleted
- **WHEN** a detached series draft is deleted after reassignment to a different congregation or category
- **THEN** the original series occurrence remains eligible for generation

#### Scenario: Deleted recurring series occurrence
- **WHEN** a planner removes one unreleased series occurrence and a scheduler regenerates the same series
- **THEN** that occurrence stays deleted while other dates in the series may still be generated

### Requirement: Zeitkonsistente Aktualisierung von Planungsserien
Beim Ändern einer Planungsserie SHALL der Router `updated_at` als zeitzonenbewussten UTC-Zeitstempel speichern, konsistent mit der initialen Erzeugung. Der Zeitstempel SHALL nicht in eine naive lokale Zeit umgewandelt werden.

#### Scenario: Planungsserie wird geändert
- **WHEN** ein berechtigter Bezirksadministrator eine Planungsserie aktualisiert
- **THEN** ist `updated_at` UTC-bewusst und nicht älter als der zuvor gespeicherte UTC-Zeitstempel
