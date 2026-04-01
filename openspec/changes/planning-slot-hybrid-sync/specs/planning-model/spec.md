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
