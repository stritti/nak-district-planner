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
