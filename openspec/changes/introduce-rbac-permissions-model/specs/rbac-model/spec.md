## ADDED Requirements

### Requirement: Canonical roles
The system SHALL define canonical roles: DISTRICT_ADMIN, CONGREGATION_ADMIN, PLANNER, VIEWER.

#### Scenario: Role assignment
- **WHEN** a user is assigned a role
- **THEN** the system SHALL store role and scope via Membership

### Requirement: Scoped permissions
The system SHALL support role assignments scoped to either District or Congregation.

#### Scenario: Congregation-scoped planner
- **WHEN** a PLANNER is assigned to a specific Congregation
- **THEN** the user SHALL only modify PlanningSlots within that Congregation

### Requirement: Authorization enforcement
The system SHALL enforce authorization checks before executing protected use cases.

#### Scenario: Unauthorized modification
- **WHEN** a VIEWER attempts to modify a PlanningSlot
- **THEN** the system SHALL deny the operation
