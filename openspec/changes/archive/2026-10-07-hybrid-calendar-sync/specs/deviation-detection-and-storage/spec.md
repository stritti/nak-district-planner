## ADDED Requirements

### Requirement: External time changes stored as deviation
The system SHALL treat external datetime changes as deviations rather than structural mutations.

#### Scenario: External time shift creates deviation
- **WHEN** an external system modifies the start time of a synced event
- **THEN** the system SHALL store the new time in `EventInstance.actual_start`
- **THEN** the system SHALL set `EventInstance.deviation_flag = true`
- **THEN** the `PlanningSlot.planning_time` SHALL remain unchanged

#### Scenario: Multiple external time shifts
- **WHEN** an external system modifies the start time multiple times
- **THEN** the system SHALL update `EventInstance.actual_start` with the latest value
- **THEN** `deviation_flag` SHALL remain true until the deviation is resolved

#### Scenario: Deviation cleared
- **WHEN** an administrator manually resolves a deviation
- **THEN** the system SHALL set `deviation_flag = false` and sync the corrected time back to the external calendar
