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

#### Scenario: Idempotent repeated sync
- **WHEN** an unchanged feed is synchronized twice
- **THEN** the second run creates, updates and cancels nothing

### Requirement: Floating and all-day times
Floating date-times and all-day dates SHALL be interpreted in `SYNC_DEFAULT_TIMEZONE` (default Europe/Berlin).

#### Scenario: Floating time in summer
- **WHEN** a floating event starts at 19:30 on 2026-04-01
- **THEN** it is stored as 17:30 UTC

#### Scenario: All-day event
- **WHEN** an all-day event is dated 2026-04-18
- **THEN** it starts at 2026-04-17 22:00 UTC and ends one day later

### Requirement: Window-bounded deletion detection
ICS and CalDAV results SHALL be treated as authoritative snapshots: a linked event missing from the result SHALL be cancelled according to the integration's `delete_behavior` only when its instance lies inside the queried window.

#### Scenario: Removed feed event
- **WHEN** a previously linked event inside the window disappears from the ICS feed
- **THEN** its planning slot is cancelled (MARK_CANCELLED) or deleted (HARD_DELETE)

#### Scenario: Event outside the window
- **WHEN** a linked event starts after the window end
- **THEN** it is not cancelled although it is absent from the result

#### Scenario: Legacy series link
- **WHEN** a series was linked under its plain UID before occurrence identities existed
- **THEN** the occurrence starting at the linked instance's start takes over the link and the slot stays active
