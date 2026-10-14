## ADDED Requirements

### Requirement: Planning structure separation
The system SHALL separate normative planning structure from execution state using PlanningSeries, PlanningSlot, and EventInstance.

#### Scenario: Slot identity independent of execution time
- **WHEN** an external system changes the start time of an event
- **THEN** the PlanningSlot identity and matrix position SHALL remain unchanged

### Requirement: Series-based slot generation
The system SHALL support PlanningSeries that generate PlanningSlots for recurring services.

#### Scenario: Rolling slot generation
- **WHEN** a PlanningSeries is active
- **THEN** the system SHALL generate PlanningSlots at least 6 months ahead

### Requirement: Aggregate retention cleanup
The system SHALL apply event retention to the PlanningSlot aggregate root and SHALL NOT leave orphaned EventInstance rows.

#### Scenario: Slot older than retention cutoff
- **WHEN** a PlanningSlot has a `planning_date` strictly before the 24-month retention cutoff
- **THEN** the cleanup SHALL delete the PlanningSlot
- **AND** its dependent EventInstance SHALL be deleted by the database cascade

#### Scenario: Slot exactly on retention cutoff
- **WHEN** a PlanningSlot has a `planning_date` equal to the retention cutoff
- **THEN** the cleanup SHALL retain the PlanningSlot
- **AND** its EventInstance SHALL remain intact

#### Scenario: Cleanup transaction is audited
- **WHEN** retention cleanup deletes one or more PlanningSlots
- **THEN** the system SHALL persist one bulk-deletion audit entry in the same transaction
