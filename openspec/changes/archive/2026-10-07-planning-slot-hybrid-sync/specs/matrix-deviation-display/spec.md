## ADDED Requirements

### Requirement: Matrix based on PlanningSlot
The system SHALL render the matrix view using PlanningSlot as the authoritative source.

#### Scenario: Render slot in matrix
- **WHEN** the matrix is requested
- **THEN** it SHALL display entries based on PlanningSlot planning_date and congregation

### Requirement: Visible deviation indicator
The system SHALL visually indicate deviations between planned and actual time.

#### Scenario: Time deviation exists
- **WHEN** deviation_flag is true
- **THEN** the matrix SHALL display planned time and actual time
