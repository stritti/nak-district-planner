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

### Requirement: Responsible person of an event
Every event, not only a `Gottesdienst`, MAY have one responsible person, stored as its single assignment. `GET /api/v1/events` SHALL expose it as `responsible` (`assignment_id`, `leader_id`, `name`, `status`) and SHALL NOT resolve a leader of another district.

#### Scenario: Non-service event with a responsible person
- **WHEN** a planner assigns a person to an event of another category
- **THEN** the event list returns that person as `responsible`

### Requirement: Pinned horizontal scrollbar
When the matrix is wider than its container, its horizontal scrollbar SHALL stay at the bottom edge of the visible viewport, even while the table extends further down, and SHALL stay in sync with the table's horizontal scroll position.

#### Scenario: Tall and wide matrix on a small screen
- **WHEN** the matrix is wider and taller than the viewport
- **THEN** the horizontal scrollbar is visible at the bottom of the viewport without scrolling to the end of the table

### Requirement: Compact leader selection
The leader field of the assignment modal SHALL be the first input of the modal. Its suggestion list SHALL be compact, SHALL stay inside the visible viewport (opening upwards when there is no room below) and SHALL pre-select the best match while the user types, so that Enter or Tab confirms it. Text that equals a known name SHALL count as that choice when the field is left; other text SHALL remain a free-text entry.

#### Scenario: Long leader list on a small screen
- **WHEN** the district has dozens of leaders and the modal is open on a small screen
- **THEN** the suggestion list is fully visible, and typing part of a name highlights the first match, which Enter selects

