## ADDED Requirements

### Requirement: Governed external event ingestion
The system SHALL not automatically create PlanningSlots for newly detected external events.

#### Scenario: New external event without mapping
- **WHEN** an external event is detected with no existing mapping
- **THEN** the system SHALL create an ExternalEventCandidate

### Requirement: Auto-matching exact slot
The system SHALL automatically map an external event to an existing PlanningSlot if congregation, date, time, and category match exactly.

#### Scenario: Exact match
- **WHEN** an external event matches an existing PlanningSlot exactly
- **THEN** the system SHALL create a mapping without creating a candidate
