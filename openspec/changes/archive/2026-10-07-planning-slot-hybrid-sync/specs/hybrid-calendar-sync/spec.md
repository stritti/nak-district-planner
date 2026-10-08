## ADDED Requirements

### Requirement: Field-level sync authority
The system SHALL enforce field-level authority rules for calendar synchronization.

#### Scenario: Structural field change from external
- **WHEN** an external system attempts to modify a structural field
- **THEN** the system SHALL ignore the structural change

### Requirement: Time deviation handling
The system SHALL treat external datetime changes as deviations rather than structural mutations.

#### Scenario: External time shift
- **WHEN** an external system modifies the start time
- **THEN** the system SHALL store the change in EventInstance and mark deviation_flag = true

### Requirement: Symmetric deletion
The system SHALL propagate deletions bidirectionally between internal and external systems.

#### Scenario: External deletion
- **WHEN** an external event is deleted
- **THEN** the corresponding PlanningSlot SHALL be soft-deleted internally
