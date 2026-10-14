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

### Requirement: Bounded sync window
The system SHALL query every calendar provider with a bounded window from `now - SYNC_WINDOW_PAST_DAYS` (default 62) to `now + SYNC_WINDOW_FUTURE_MONTHS` (default 24). Connectors SHALL omit unset bounds instead of sending empty values.

#### Scenario: Provider query carries both bounds
- **WHEN** a sync runs
- **THEN** the connector receives `from_dt = now - 62 days` and `to_dt = now + 24 months`

#### Scenario: CalDAV omits unset bounds
- **WHEN** the CalDAV connector is called without `to_dt`
- **THEN** the `C:time-range` element contains no `end` attribute and no empty attribute value

### Requirement: Recurring series expansion
ICS and CalDAV connectors SHALL expand recurring series into individual occurrences inside the window, honouring EXDATE and RECURRENCE-ID overrides, and SHALL identify each occurrence by `UID::RECURRENCE-ID` while non-recurring events keep their plain UID.

#### Scenario: Weekly series across a DST change
- **WHEN** a weekly 10:00 Europe/Berlin series crosses 2026-03-29
- **THEN** occurrences before the change start at 09:00 UTC and occurrences after it at 08:00 UTC

#### Scenario: Excluded and overridden occurrences
- **WHEN** one occurrence is listed in EXDATE and another has a RECURRENCE-ID override
- **THEN** the excluded occurrence is absent and the override replaces the generated occurrence under the same identity

#### Scenario: Series started before the window
- **WHEN** a series' first occurrence lies before the window start
- **THEN** its occurrences inside the window are still returned

#### Scenario: Explicit occurrence identity
- **WHEN** an occurrence is produced from a series
- **THEN** it carries `series_uid` and `recurrence_id` explicitly, the composed storage key is never parsed back, and a plain UID containing `::` is treated as a single event

#### Scenario: Overlong UID
- **WHEN** the composed key `UID::RECURRENCE-ID` would exceed 500 characters
- **THEN** the UID part is replaced by `sha256:<hex digest of the UID>` so the key fits the external_event_id columns and stays stable

#### Scenario: Duplicate identity in one snapshot
- **WHEN** two source events map to the same storage key
- **THEN** only the first is processed and the second is counted as failed

#### Scenario: Idempotent repeated sync
- **WHEN** an unchanged feed is synchronized twice
- **THEN** the second run creates, updates and cancels nothing

### Requirement: Bounded recurrence expansion
Expansion of external feeds SHALL be bounded: rules with FREQ SECONDLY, MINUTELY or HOURLY SHALL be rejected, iteration from each series start SHALL be limited to a fixed budget (100 000 steps per feed or resource), and in-window occurrences SHALL be capped by `SYNC_MAX_OCCURRENCES` (default 5000). Exceeding a bound SHALL fail the sync with a generic error.

#### Scenario: Hostile secondly rule
- **WHEN** a feed contains `RRULE:FREQ=SECONDLY`
- **THEN** the fetch fails within seconds with a connector error and nothing is reconciled

#### Scenario: Expired dense series
- **WHEN** a series with many occurrences per day ended (UNTIL) years before the window
- **THEN** UNTIL bounds the budgeted iteration (normalized to naive UTC for aware and floating starts) and the feed is accepted

#### Scenario: Too many occurrences
- **WHEN** a feed expands into more in-window occurrences than `SYNC_MAX_OCCURRENCES`
- **THEN** the fetch fails with a connector error

### Requirement: Event duration
An event without DTEND and DURATION SHALL last one day; an explicit zero-length event (DTEND equal to DTSTART or DURATION:PT0S) SHALL stay zero-length.

#### Scenario: Open-ended event
- **WHEN** a VEVENT has neither DTEND nor DURATION
- **THEN** each of its occurrences ends one calendar day after it starts, counted in the event's time zone (an all-day event on a DST change day ends at the next local midnight)

#### Scenario: Explicit zero length
- **WHEN** a VEVENT has DTEND equal to DTSTART or DURATION:PT0S
- **THEN** its end equals its start

### Requirement: No write-back of series occurrences
Time updates and deletions SHALL be refused for links that identify a single occurrence of a recurring series, before any provider call. Because links store only the composed key, a stored key ending in `::YYYYMMDD` or `::YYYYMMDDTHHMMSSZ` SHALL be treated as an occurrence (fail-safe: a plain UID of that shape only loses write-back). The API SHALL answer such a refusal with HTTP 409.

#### Scenario: Resolving a deviation of an occurrence
- **WHEN** a planner resolves a deviation or conflict on an instance linked to a series occurrence of a writable integration
- **THEN** no provider write happens, the local state stays retryable and the API responds 409

#### Scenario: Single events stay writable
- **WHEN** the linked event is a single event
- **THEN** the times are written back as before

### Requirement: Floating and all-day times
Floating date-times and all-day dates SHALL be interpreted in the feed's `X-WR-TIMEZONE` if it names a valid zone, otherwise in `SYNC_DEFAULT_TIMEZONE` (default Europe/Berlin), consistently for occurrences inside and events outside the window. Day-based durations SHALL be nominal: counted on the wall clock of the start's zone.

#### Scenario: Floating time in summer
- **WHEN** a floating event starts at 19:30 on 2026-04-01
- **THEN** it is stored as 17:30 UTC

#### Scenario: Feed declares its zone
- **WHEN** a feed with `X-WR-TIMEZONE:America/New_York` contains floating events inside and outside the window
- **THEN** both are interpreted in America/New_York

#### Scenario: Day duration across a DST change
- **WHEN** an event starts at local midnight on a DST change day with `DURATION:P1D`
- **THEN** it ends at the next local midnight

#### Scenario: All-day event
- **WHEN** an all-day event is dated 2026-04-18
- **THEN** it starts at 2026-04-17 22:00 UTC and ends one day later

### Requirement: Window-bounded deletion detection
ICS and CalDAV results SHALL be treated as authoritative snapshots: a linked event missing from the result SHALL be cancelled according to the integration's `delete_behavior` only when its instance lies inside the queried window. The window is half-open like the provider query: an instance ending exactly at the window start or starting exactly at the window end is outside.

#### Scenario: Incomplete snapshot
- **WHEN** a CalDAV resource in the window has missing, empty or unparseable calendar data, or an ICS feed contains an unparseable VEVENT or a VEVENT without UID
- **THEN** the remaining events are processed, no deletion reconciliation runs for that sync, a warning without provider identifiers is logged and the integration's last sync error states that reconciliation was skipped, also when individual events failed in the same sync

#### Scenario: Removed feed event
- **WHEN** a previously linked event inside the window disappears from the ICS feed
- **THEN** its planning slot is cancelled (MARK_CANCELLED) or deleted (HARD_DELETE)

#### Scenario: Event outside the window
- **WHEN** a linked event starts after the window end
- **THEN** it is not cancelled although it is absent from the result

#### Scenario: Event touching a window bound
- **WHEN** a linked event ends exactly at the window start or starts exactly at the window end and is absent from the result
- **THEN** it is not cancelled

#### Scenario: Event moved outside the window
- **WHEN** a linked single event or override is moved by the provider to a time outside the window
- **THEN** the ICS connector reports it as present outside the window, the linked instance is updated and the slot is not cancelled

#### Scenario: CalDAV resource missing from the window result
- **WHEN** a linked CalDAV resource is absent from the time-range result
- **THEN** the slot is cancelled only if a GET on the stored resource href returns 404 or 410; if the resource still exists, has no stored href or the check fails, nothing is cancelled
- **AND** a missing occurrence of a resource that was returned is reconciled without a check

#### Scenario: Event restored after a snapshot gap
- **WHEN** a slot was cancelled because its event was missing from a snapshot and the event reappears uncancelled
- **THEN** the slot is reactivated unless a planner edited or confirmed it since (instance DIRTY_INTERNAL or CONFLICT), while slots cancelled by planners or by provider STATUS:CANCELLED stay cancelled; a STATUS:CANCELLED seen after a snapshot gap replaces the gap marker, so a later un-cancel does not reactivate the slot

#### Scenario: Legacy series link
- **WHEN** a series was linked under its plain UID before occurrence identities existed
- **THEN** the occurrence starting at the linked instance's start, or an override whose RECURRENCE-ID names that start, takes over the link and the slot stays active
