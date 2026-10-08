# district-administration Specification

## Purpose

Covers management of the tenant structure and people: districts, congregations with service times, congregation groups, service leaders, leader self-linking and leader unavailability.

## Requirements

### Requirement: Districts and congregations
Only superadmins SHALL create districts; `DISTRICT_ADMIN` SHALL update a district and create congregations; `DISTRICT_ADMIN` or the congregation's `CONGREGATION_ADMIN` SHALL update a congregation; `VIEWER` SHALL list congregations. A district MAY carry a German `state_code` used for holiday import.

#### Scenario: District admin creates a district
- **WHEN** a non-superadmin posts to `/api/v1/districts`
- **THEN** the API responds with 403

### Requirement: Congregation groups
Congregations SHALL be assignable to zero or one group of the same district. Group CRUD under `/api/v1/districts/{id}/groups` SHALL require `DISTRICT_ADMIN` for writes and `VIEWER` for reads. Overviews SHALL render grouped sections plus an ungrouped section, and creation dialogs SHALL expose all creation options including the group.

#### Scenario: Group from another district
- **WHEN** a congregation is assigned to a group of another district
- **THEN** the request is rejected with a validation error

### Requirement: Service leaders
Leaders SHALL be managed under `/api/v1/districts/{id}/leaders` (`VIEWER` read, `PLANNER` write). An authenticated member SHALL be able to link, inspect and remove the link of their own user account to a leader record via `/link-self`.

#### Scenario: Viewer creates a leader
- **WHEN** a viewer posts a new leader
- **THEN** the API responds with 403

### Requirement: Leader unavailability
Leader unavailability periods SHALL be managed per district leader (`VIEWER` read, `PLANNER` write) and SHALL be considered by assignment conflict checks.

#### Scenario: Unavailability recorded
- **WHEN** a planner records an unavailability period for a leader
- **THEN** subsequent assignments of that leader within the period are reported as conflicts
