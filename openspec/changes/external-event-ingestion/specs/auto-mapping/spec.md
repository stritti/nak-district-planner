## ADDED Requirements

### Requirement: Auto-matching exact slot
The system SHALL automatically map an external event to an existing `PlanningSlot` if congregation, date, time, and category match exactly.

#### Scenario: Exact match skips candidate creation
- **WHEN** an external event matches an existing `PlanningSlot` on congregation_id, planning_date, planning_time, and category
- **THEN** the system SHALL create a mapping without creating an `ExternalEventCandidate`

#### Scenario: Partial match creates candidate
- **WHEN** an external event matches on congregation and date but NOT on time or category
- **THEN** the system SHALL create an `ExternalEventCandidate` for manual review
