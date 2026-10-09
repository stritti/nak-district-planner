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

#### Scenario: Unassigned service
- **WHEN** a `Gottesdienst` slot has no service assignment
- **THEN** its cell has `is_gap = true` and the UI renders it as a red "LÜCKE" cell that opens the assignment modal

#### Scenario: Holiday without regular service
- **WHEN** a `Feiertag` falls on a date without regular services
- **THEN** the date still appears as a column with the holiday name

### Requirement: Service assignments API
Assignments SHALL be managed under `/api/v1/events/{event_id}/assignments` (`POST`, `GET`, `PUT /{id}`, `DELETE /{id}`). Reading SHALL require `VIEWER`, writing `PLANNER` in the slot's district. An assignment SHALL reference a leader ID or a free-text leader name and have status `OPEN`, `ASSIGNED` or `CONFIRMED`. Newly confirming an assignment SHALL publish `ASSIGNMENT_CONFIRMED` after commit. Assignments are not limited to `Gottesdienst` slots: every event may have one responsible person. `GET /api/v1/events` SHALL expose it as `responsible` (`assignment_id`, `leader_id`, `name`, `status`) and SHALL NOT resolve a leader of another district.

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
