## ADDED Requirements

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
