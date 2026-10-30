## ADDED Requirements

### Requirement: Assignments are checked against planning conflicts
Before a leader is assigned to a service, the system SHALL evaluate the domain conflict rules (double booking, travel time between congregations, required ministry level, leader unavailability) and SHALL classify each finding as `PASS`, `WARN` or `BLOCK`. The check SHALL be enabled by default and only be disabled through `CONFLICT_CHECK_ENABLED=false`.

#### Scenario: Overlapping assignment is blocked
- **WHEN** a leader is assigned to a service that overlaps another assignment of the same leader
- **THEN** the API responds with 409 and a conflict list containing a `BLOCK` finding
- **AND** no assignment is stored

#### Scenario: Adjacent services are not a double booking
- **WHEN** one service ends exactly when the next service of the same leader starts
- **THEN** no double-booking finding is reported

#### Scenario: Leader is unavailable
- **WHEN** the service lies within a recorded unavailability period of the leader
- **THEN** the API responds with 409 and a `BLOCK` finding

### Requirement: Warnings require explicit confirmation
Findings of severity `WARN` (e.g. less than `MIN_TRAVEL_MINUTES` between services in different congregations) SHALL NOT be stored silently: the API SHALL respond with 409 and the conflict list unless the request sets `confirm_warnings: true`.

#### Scenario: Short travel time without confirmation
- **WHEN** an assignment leaves less than `MIN_TRAVEL_MINUTES` between two services in different congregations and `confirm_warnings` is false
- **THEN** the API responds with 409 and a `WARN` finding

#### Scenario: Short travel time with confirmation
- **WHEN** the same request is repeated with `confirm_warnings: true`
- **THEN** the assignment is stored

### Requirement: Leader unavailability is managed per district
Leader unavailability periods (reason `URLAUB`, `SPERRZEIT`, `FORTBILDUNG`, `SONSTIGES`) SHALL be readable with `VIEWER` and writable only with `PLANNER` or higher in the leader's district.

#### Scenario: Viewer cannot record an absence
- **WHEN** a user with only `VIEWER` in the district creates an unavailability period
- **THEN** the API responds with 403
