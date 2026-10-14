## ADDED Requirements

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
