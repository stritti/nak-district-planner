# service-assignment-matrix Specification

## Purpose

Describes the district planning matrix (UC-03) and service-leader assignments: dates on the X axis, congregations on the Y axis, gap highlighting for unassigned services, and the assignment API with conflict checks.

## Requirements

### Requirement: Matrix API
`GET /api/v1/districts/{id}/matrix` SHALL require `VIEWER` in the district and accept optional `from_dt`, `to_dt` and `group_id`. Without a range it SHALL cover today plus 27 days; with one bound it SHALL cover 28 days ending or starting there. An unknown district SHALL respond with 404.

#### Scenario: Default range
- **WHEN** the matrix is requested without dates
- **THEN** it covers the next 4 weeks starting today

### Requirement: Matrix columns and cells
Columns SHALL be the union of dates expected by congregation `service_times`, dates of `Feiertag` slots (always shown, names in `holidays`) and dates of `Gottesdienst` slots. A cell SHALL resolve the congregation's `Gottesdienst` slot (earliest time on that date) or a district-level slot and expose approval status, assignment status and leader, `is_gap` (no assignment and not an invitation copy), deviation flag with minute differences, invitation source and invitation count.

#### Scenario: Service moved outside the regular schedule
- **WHEN** a `Gottesdienst` slot of a congregation lies on a date that is neither in its `service_times` nor a holiday (e.g. moved from Sunday to Saturday)
- **THEN** its cell shows the slot and remains assignable instead of being rendered empty

#### Scenario: Assign from the event list
- **WHEN** a planner edits an event in the event list and enters a person in the "Dienstleiter:in" (Gottesdienst) or "Verantwortliche:r" (other event) field
- **THEN** the assignment is created, changed or removed via `/api/v1/events/{event_id}/assignments` with the same conflict handling as in the matrix, and the list shows the name (a Gottesdienst without one shows "Lücke")

#### Scenario: Invited congregation
- **WHEN** a congregation has an invitation copy on a date and its own `Gottesdienst` slot there has no assignment
- **THEN** its cell shows the copy as "Gottesdienst in [Gastgeber]" (host highlighted) with the host's leader and is no gap; the note that the leader is maintained at the host appears only as a tooltip

#### Scenario: Unassigned service
- **WHEN** a `Gottesdienst` slot has no service assignment
- **THEN** its cell has `is_gap = true` and the UI renders it as a red "LÜCKE" cell that opens the assignment modal

#### Scenario: Holiday without regular service
- **WHEN** a `Feiertag` falls on a date without regular services
- **THEN** the date still appears as a column with the holiday name

### Requirement: Service assignments API
Assignments SHALL be managed under `/api/v1/events/{event_id}/assignments` (`POST`, `GET`, `PUT /{id}`, `DELETE /{id}`). Reading SHALL require `VIEWER`, writing `PLANNER` in the slot's district. An assignment SHALL reference a leader ID or a free-text leader name and have status `OPEN`, `ASSIGNED` or `CONFIRMED`. Newly confirming an assignment SHALL publish `ASSIGNMENT_CONFIRMED` after commit.

#### Scenario: Assignment without leader
- **WHEN** an assignment is created with neither `leader_id` nor `leader_name`
- **THEN** it is rejected

### Requirement: Assignment conflict checks
When an assignment references a `leader_id`, the system SHALL evaluate configured conflict rules (for example leader unavailability or double booking). Blocking conflicts, and warnings not acknowledged with `confirm_warnings`, SHALL be rejected with 409 and a structured list of conflicts (`rule_id`, `severity`, `message`, `details`).

#### Scenario: Warning not confirmed
- **WHEN** a planner assigns a leader that triggers a `WARN` conflict without `confirm_warnings`
- **THEN** the API responds with 409 listing the warning

### Requirement: Matrix usability
The matrix view SHALL show a skeleton while loading, keep the congregation column sticky during horizontal scroll, offer a congregation text filter and an optional group-based secondary sort, and mark external time deviations with an indicator.

#### Scenario: Group sorting enabled
- **WHEN** the user enables group sorting
- **THEN** congregations are ordered by group and then by their existing order

### Requirement: Sticky matrix date headings
The matrix SHALL keep weekday, date and holiday headings visible at the top during vertical scrolling in its bounded two-axis scroll region. Congregation names SHALL remain pinned to the left. The top-left corner SHALL stay above both axes, with opaque header backgrounds in light, dark and compact modes.

#### Scenario: Two-axis matrix scrolling
- **WHEN** the user scrolls a tall and wide matrix vertically and horizontally
- **THEN** weekday, date and holiday headings stay at the top of the matrix scroll region, congregation names stay at the left, and the top-left corner stays visible above both

#### Scenario: Opaque holiday header in dark mode
- **WHEN** a holiday date header is sticky while the matrix scrolls in dark mode
- **THEN** its background SHALL be fully opaque so underlying cell content cannot show through

#### Scenario: Vertical overscroll at the matrix boundary
- **WHEN** the user scrolls beyond the first or last matrix row
- **THEN** the scroll gesture SHALL continue into the surrounding document without trapping vertical page navigation

#### Scenario: Short or empty matrix
- **WHEN** the matrix has fewer rows than the available space or no date columns
- **THEN** the view SHALL NOT force unnecessary vertical scrolling or render an empty sticky header

### Requirement: Responsible person of an event
Every event, not only a `Gottesdienst`, MAY have one responsible person, stored as its single assignment. `GET /api/v1/events` SHALL expose it as `responsible` (`assignment_id`, `leader_id`, `name`, `status`) and SHALL NOT resolve a leader of another district.

#### Scenario: Non-service event with a responsible person
- **WHEN** a planner assigns a person to an event of another category
- **THEN** the event list returns that person as `responsible`

### Requirement: Pinned horizontal scrollbar
When the matrix is wider than its container, its horizontal scrollbar SHALL stay at the bottom edge of the visible viewport, even while the table extends further down, and SHALL stay in sync with the table's horizontal scroll position. The proxy SHALL cover the full scroll range, including when a classic vertical scrollbar reduces the matrix's usable width.

#### Scenario: Tall and wide matrix on a small screen
- **WHEN** the matrix is wider and taller than the viewport
- **THEN** the horizontal scrollbar is visible at the bottom of the viewport without scrolling to the end of the table

#### Scenario: Classic vertical scrollbar consumes content width
- **WHEN** a non-overlay vertical scrollbar reduces the matrix client width
- **THEN** the horizontal proxy viewport SHALL match the matrix client width and reach the complete rightmost date column

### Requirement: Compact leader selection
The leader field of the assignment modal SHALL be the first input of the modal. Its suggestion list SHALL be compact, SHALL stay inside the visible viewport (opening upwards when there is no room below) and SHALL pre-select the best match while the user types, so that Enter or Tab confirms it. Text that equals a known name SHALL count as that choice when the field is left; other text SHALL remain a free-text entry.

#### Scenario: Long leader list on a small screen
- **WHEN** the district has dozens of leaders and the modal is open on a small screen
- **THEN** the suggestion list is fully visible, and typing part of a name highlights the first match, which Enter selects

### Requirement: Inline responsible-person editing uses existing assignment semantics
When the event overview allows editing its responsible-person column in place, the system SHALL use the existing `/api/v1/events/{event_id}/assignments` flow, including status updates, conflicting appointments and required warning acknowledgements. A failed mutation SHALL not make the event list display the proposed person as confirmed.

#### Scenario: Assignment conflict from inline editor
- **WHEN** a planner selects a conflicting service leader in an inline cell editor
- **THEN** the existing 409 conflict policy applies and the current persisted assignment remains displayed until successfully changed

### Requirement: Matrix cells show planning conflicts
The matrix response SHALL list per cell the planning conflicts of its leader assignment among the loaded assignments: overlapping events (blocking) and too little travel time between congregations (warning). The matrix SHALL mark such cells with a text label that does not rely on colour alone.

#### Scenario: Same rules as assigning
- **WHEN** conflicts are computed
- **THEN** they use the rules and default duration of the assignment conflict checks
- **AND** the list is empty when conflict checks are disabled or the assignment is a free-text guest

#### Scenario: Overlapping events of one leader
- **WHEN** one leader is assigned to two events that overlap, in the same or in different congregations
- **THEN** both cells carry a `no_double_booking` conflict with severity `BLOCK`
- **AND** the matrix marks both with "Konflikt"

#### Scenario: Short travel time
- **WHEN** one leader has events in two congregations with less than the configured travel time between them
- **THEN** both cells carry a `travel_time_check` conflict with severity `WARN` and the matrix marks them with "Warnung"

#### Scenario: Different leaders
- **WHEN** two different leaders are assigned to overlapping events
- **THEN** no conflict is reported

#### Scenario: Multiple services on the same day
- **WHEN** a congregation has more than one visible service on the same date
- **THEN** the matrix cell reports the number of services and aggregates conflicts from all of them
- **AND** conflict messages include the affected service time to distinguish same-day assignments

#### Scenario: Unassigned primary service
- **WHEN** the earliest service is unassigned and a later service has a planning conflict
- **THEN** the daily cell SHALL display both the gap and the aggregated conflict marker
- **AND** the service count SHALL remain visible

#### Scenario: Inline assignment update
- **WHEN** a leader assignment is saved inline
- **THEN** the matrix reloads the authoritative conflicts for all cells in the selected range
- **AND** stale conflict indicators are hidden until the refresh succeeds
- **AND** the UI makes a failed conflict refresh visible without misrepresenting the assignment save as failed
