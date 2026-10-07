## ADDED Requirements

### Requirement: Generate draft worship services 8 weeks ahead
The system SHALL generate worship service events as drafts for each congregation based on its configured standard service times for a rolling horizon of 8 weeks in advance.

#### Scenario: Generate future draft services from standard times
- **WHEN** the pre-generation process runs for a congregation with valid standard service times
- **THEN** the system creates draft worship service events for all matching time slots within the next 8 weeks

### Requirement: Generated services start without leader assignment
The system SHALL create all auto-generated worship service events without any service leader assignment.

#### Scenario: Draft service has no assigned leader
- **WHEN** a worship service event is created by the pre-generation process
- **THEN** the event has no `ServiceAssignment` and no leader is assigned

### Requirement: Pre-generation is idempotent
The system SHALL avoid creating duplicate draft worship service events when the pre-generation process is executed multiple times for the same congregation and time slots.

#### Scenario: Re-running generation does not duplicate events
- **WHEN** the pre-generation process is run again for a period where matching generated draft events already exist
- **THEN** the system does not create additional duplicate draft events for those same slots

### Requirement: Moved generated services are not recreated at original slot
The system SHALL keep a stable identity for each generated standard service slot so that when a generated event is manually moved to another date/time, later pre-generation runs do not recreate a new event at the original standard slot.

#### Scenario: Wednesday service moved to Thursday for holiday
- **WHEN** a generated Wednesday draft service is manually moved to Thursday (for example due to Christi Himmelfahrt)
- **THEN** subsequent pre-generation runs do not create another new draft service at the original Wednesday slot for that same planned occurrence

### Requirement: Maintain rolling 8-week planning window
The system SHALL support periodic execution of pre-generation so that each congregation continuously has draft worship services available up to 8 weeks ahead.

#### Scenario: Periodic run fills newly opened future slots
- **WHEN** time progresses and the periodic pre-generation process runs
- **THEN** the system creates draft worship service events for newly opened slots so the horizon remains 8 weeks ahead
