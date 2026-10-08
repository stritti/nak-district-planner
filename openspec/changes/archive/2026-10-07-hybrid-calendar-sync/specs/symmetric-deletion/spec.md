## ADDED Requirements

### Requirement: Symmetric deletion propagation
The system SHALL propagate deletions bidirectionally between internal and external calendars.

#### Scenario: External deletion soft-deletes internally
- **WHEN** an external event is deleted in the source calendar
- **THEN** the corresponding `PlanningSlot` SHALL be soft-deleted (`cancelled` status)
- **THEN** the corresponding `EventInstance` SHALL be soft-deleted

#### Scenario: Internal deletion pushes to external
- **WHEN** a `PlanningSlot` is deleted internally
- **THEN** the system SHALL push a deletion to the external calendar via the registered `CalendarConnector`

#### Scenario: Self-initiated deletion not propagated back
- **WHEN** a sync event is received that corresponds to a deletion the system itself initiated
- **THEN** the system SHALL ignore the incoming deletion to prevent loops
