# calendar-sync Specification

## Purpose

Describes the bidirectional, hash-based synchronisation between linked external calendar events and internal `EventInstance`/`PlanningSlot` records (UC-02), including scheduling, idempotency, the sync state machine, field-level authority, time deviations, symmetric deletion and failure handling. This capability consolidates the former `uc-02-zyklischer-sync`, `harden-calendar-sync-algorithm`, `hybrid-calendar-sync` and `planning-slot-hybrid-sync` deltas.

## Requirements

### Requirement: Scheduled and manual synchronisation
The Celery beat schedule SHALL register `sync_all_active_integrations` every 5 minutes; it SHALL dispatch `sync_calendar_integration` for every active integration that was never synced or whose `sync_interval` has elapsed. `POST /api/v1/calendar-integrations/{id}/sync` SHALL run one sync synchronously for a `DISTRICT_ADMIN` of the integration's district and return the outcome counts (`created`, `updated`, `cancelled`, `auto_matched`, `skipped`, `failed`).

#### Scenario: Interval not yet elapsed
- **WHEN** the periodic task runs and an integration was synced fewer than `sync_interval` minutes ago
- **THEN** no sync task is dispatched for it

#### Scenario: Manual sync
- **WHEN** a district admin triggers a manual sync
- **THEN** the response contains the per-outcome counts of that run

### Requirement: Serialised, windowed sync runs
A sync run SHALL acquire a PostgreSQL transaction-scoped advisory lock derived from the integration ID before processing, and SHALL fetch provider events starting 62 days in the past.

#### Scenario: Concurrent runs for one integration
- **WHEN** two sync runs for the same integration start concurrently
- **THEN** the second waits for the first transaction to finish before processing events

### Requirement: Idempotent processing via content hash
Each fetched event SHALL receive a SHA-256 content hash over UID, start, end, title, description and cancellation flag. An event whose hash equals the link's `last_synced_hash` SHALL be skipped; repeated runs SHALL NOT create duplicates.

#### Scenario: Unchanged external event
- **WHEN** an already linked event is fetched with an unchanged hash
- **THEN** no internal record is modified and the outcome is `skipped`

#### Scenario: Changed external event
- **WHEN** a linked event is fetched with a different hash and no unresolved local change
- **THEN** its soft and conditional fields are applied, the instance is marked `DIRTY_EXTERNAL` and the link baseline is advanced

### Requirement: Deterministic sync state machine
`EventInstance.sync_state` SHALL be one of `CLEAN`, `DIRTY_INTERNAL`, `DIRTY_EXTERNAL`, `CONFLICT`. Internal edits SHALL move `CLEAN`/`DIRTY_INTERNAL` to `DIRTY_INTERNAL` and `DIRTY_EXTERNAL`/`CONFLICT` to `CONFLICT`; changed inbound data SHALL move `DIRTY_INTERNAL`/`CONFLICT` to `CONFLICT` and other states to `DIRTY_EXTERNAL`.

#### Scenario: Internal edit of a linked event
- **WHEN** a planner changes title, status, description or times of an event with an `EventInstance`
- **THEN** the instance's sync state transitions according to the internal transition rule

#### Scenario: Overlapping internal and external changes
- **WHEN** an inbound change touches a field that was also changed locally, touches a non-soft field, or no baseline payload exists while the instance is `DIRTY_INTERNAL`
- **THEN** the instance transitions to `CONFLICT` and no inbound field is applied

#### Scenario: Non-overlapping soft change during local edit
- **WHEN** only soft fields changed externally and they do not overlap local changes
- **THEN** they are applied and the instance stays `DIRTY_INTERNAL`

### Requirement: Field-level sync authority
A code-defined mapping SHALL classify synchronised fields as `STRUCTURAL` (planning structure such as congregation, date, time, category, approval status, applicability), `SOFT` (`title`, `description`) or `CONDITIONAL` (`actual_start_at`, `actual_end_at`, `status`). External data SHALL never overwrite structural fields; unclassified fields SHALL be treated as structural and logged. The mapping SHALL NOT be configurable via API.

#### Scenario: Unclassified field
- **WHEN** the sync encounters a field that is not in the mapping
- **THEN** it is treated as `STRUCTURAL` and a warning is logged

### Requirement: External time changes are stored as deviations
External start/end changes SHALL be written to `EventInstance.actual_start_at`/`actual_end_at` only; `PlanningSlot.planning_date`/`planning_time` SHALL remain unchanged. `deviation_flag` SHALL be set when start or expected end differ from the slot by more than 5 minutes (expected duration from `SYNC_EXPECTED_DURATION_MINUTES`).

#### Scenario: External time shift
- **WHEN** a linked external event moves by more than 5 minutes
- **THEN** the instance holds the new times, `deviation_flag` is true and the slot keeps its planned time

### Requirement: Deviation and conflict resolution
`POST /api/v1/events/{id}/resolve-deviation` and `POST /api/v1/events/{id}/resolve-conflict` SHALL require `PLANNER` in the slot's district. Resolution SHALL favour internal planning data and push it to writable (`WRITE` capability) provider links, advancing the link baseline so the echoed provider state is not re-imported as a change. A failed provider push SHALL restore the unresolved state and respond with 502.

#### Scenario: No active conflict
- **WHEN** resolve-conflict is called for an instance not in `CONFLICT`
- **THEN** the API responds with 409

#### Scenario: Provider push fails
- **WHEN** the connector raises `CalendarConnectorError` while pushing a resolved conflict
- **THEN** the instance returns to `CONFLICT` and the API responds with 502

### Requirement: Outbound time changes for writable integrations
For an integration with `WRITE` capability, a `DIRTY_INTERNAL` instance without deviation whose times differ from an otherwise unchanged provider event SHALL be pushed via `update_event_times`; the acknowledged revision and payload SHALL become the new baseline and the instance SHALL return to `CLEAN`.

#### Scenario: Internal reschedule pushed
- **WHEN** a planner moves a linked event and the provider copy is unchanged since the last sync
- **THEN** the next sync updates the provider event and the instance becomes `CLEAN`

### Requirement: Symmetric deletion
External cancellations, and links missing from an authoritative provider snapshot within the window, SHALL apply the integration's `delete_behavior`; unresolved local changes SHALL turn such a deletion into a `CONFLICT`. An internally cancelled slot of a writable integration SHALL be deleted at the provider exactly once and SHALL NOT be re-imported.

#### Scenario: External deletion with MARK_CANCELLED
- **WHEN** a linked provider event is cancelled and `delete_behavior` is `MARK_CANCELLED`
- **THEN** the planning slot status becomes `CANCELLED` and the slot is retained

#### Scenario: External deletion with HARD_DELETE
- **WHEN** a linked provider event is cancelled and `delete_behavior` is `HARD_DELETE`
- **THEN** the slot is deleted and the link becomes a `SYNC_TOMBSTONE` with deletion origin `EXTERNAL` and a reason

#### Scenario: Internal cancellation pushed
- **WHEN** a planner cancels a slot linked to a writable integration whose provider copy is unchanged
- **THEN** the next sync deletes the provider event, stores the `internal:deleted` revision marker and tombstones the link

#### Scenario: External deletion with local changes
- **WHEN** a linked provider event is cancelled while its instance is `DIRTY_INTERNAL`
- **THEN** the instance becomes `CONFLICT` and the slot is not cancelled

#### Scenario: Self-initiated deletion
- **WHEN** a later sync sees a link tombstoned after an internal deletion
- **THEN** the event is skipped and nothing is recreated

### Requirement: Failure isolation, retry and alerting
A connector error for a single event SHALL count as `failed` without aborting the run, and the integration's `last_sync_error` SHALL record a provider-neutral summary. The Celery sync task SHALL retry with exponential backoff (base 60 s, max 3600 s, jitter, up to 4 retries), log each attempt without exception text, and create one sync-failure alert (notification and `SYNC_ERROR` domain event) after retries are exhausted.

#### Scenario: Provider unavailable
- **WHEN** every retry of a sync task fails
- **THEN** the failure is logged with integration ID, error class and attempt count and an alert is raised once
