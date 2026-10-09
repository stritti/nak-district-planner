## ADDED Requirements

### Requirement: Optional organisational duties on planning slots
A `PlanningSlot` SHALL support zero or more organisational duty assignments independently of its existing single liturgical service-leader assignment. Each assignment SHALL reference a configured category and an eligible person belonging to the authorised district/event context. A slot SHALL remain valid, confirmable and publishable with no organisational assignments.

#### Scenario: Unassigned service
- **WHEN** a Gottesdienst planning slot is created with no persons selected for Schließdienst, Organist or Dirigent
- **THEN** the slot can be saved and confirmed without additional validation errors

#### Scenario: Existing leader assignment
- **WHEN** a slot already has one liturgical service leader
- **THEN** assigning multiple organisational duty types does not violate the unique service-leader constraint

### Requirement: Validate category, person and capacity
The system SHALL reject unknown or cross-tenant category/person identifiers, assignments to categories not enabled for the slot's effective event category, duplicate person-duty pairs and assignments exceeding configured duty capacity. Checks and writes SHALL be concurrency safe, with no partial writes on failure.

#### Scenario: Concurrent final-place assignment
- **WHEN** two requests concurrently fill the last available position in a duty category
- **THEN** at most the configured capacity is persisted and the losing request receives a conflict response

#### Scenario: Foreign person
- **WHEN** a planner tries to assign a person outside the authorised district/event scope
- **THEN** the system rejects the operation without exposing foreign-person details

#### Scenario: Multiple tasks for one person
- **WHEN** the same person is assigned Organist and Schließdienst on the same slot
- **THEN** two task assignments are persisted and can be projected as one calendar event with both task labels

### Requirement: Scoped assignment management
Only planners with edit permissions for the relevant planning slot SHALL create, replace or remove organisational duty assignments. The system SHALL enforce membership and district isolation for event and person lookups.

#### Scenario: Viewer attempts reassignment
- **WHEN** a user with only `VIEWER` permissions modifies a duty assignment
- **THEN** the request is rejected and the assignment remains unchanged

### Requirement: Assignment lifecycle independent of external sync
Assignments SHALL be bound to `PlanningSlot`; EventInstance creation, replacement or incoming synchronisation SHALL not duplicate or silently erase them.

#### Scenario: External event time changes
- **WHEN** an external update changes the linked EventInstance time
- **THEN** the existing organisational duty assignment remains on the slot and displays using the resolved event time
