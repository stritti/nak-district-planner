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
The system SHALL persist a stable generation key on each generated planning slot, derived from the congregation and the local date of the standard service occurrence (not its time), so that a generated service that is manually moved or cancelled is not recreated by later pre-generation runs.

#### Scenario: Wednesday service moved to Thursday for holiday
- **WHEN** a generated Wednesday draft service is manually moved to Thursday (for example due to Christi Himmelfahrt)
- **THEN** subsequent pre-generation runs do not create another new draft service at the original Wednesday slot for that same planned occurrence

#### Scenario: Generated draft moved by planner is not regenerated
- **WHEN** a generated draft service for 10:00 is moved by a planner to 09:30 on the same day
- **THEN** the next pre-generation run does not create a new draft service at 10:00 and the matrix shows exactly one service for that congregation and day

#### Scenario: Cancelled generated service is not resurrected
- **WHEN** a planner cancels a generated draft service (status `CANCELLED`)
- **THEN** subsequent pre-generation runs treat the occurrence as existing and do not create a new active draft for it

#### Scenario: Legacy slot without generation key is adopted
- **WHEN** a pre-generation run finds a Gottesdienst slot of the congregation without generation key at the generated date and time
- **THEN** the system treats it as the existing occurrence, stores the generation key on it and does not create a new draft

#### Scenario: Hard-deleted generated service
- **WHEN** a generated planning slot was hard-deleted (no row with its generation key remains)
- **THEN** the next pre-generation run creates the occurrence again; planners suppress a single occurrence by cancelling it instead of deleting it

### Requirement: Generation key is unique per district
The system SHALL enforce at most one planning slot per generation key within a district, regardless of the slot status, and pre-generation SHALL skip an occurrence whose insert violates this rule instead of failing.

#### Scenario: Concurrent runs do not double-insert
- **WHEN** two pre-generation runs try to create the same occurrence at the same time
- **THEN** exactly one planning slot is stored and the other run skips the occurrence without failing

### Requirement: Maintain rolling 8-week planning window
The system SHALL support periodic execution of pre-generation so that each congregation continuously has draft worship services available up to 8 weeks ahead.

#### Scenario: Periodic run fills newly opened future slots
- **WHEN** time progresses and the periodic pre-generation process runs
- **THEN** the system creates draft worship service events for newly opened slots so the horizon remains 8 weeks ahead
