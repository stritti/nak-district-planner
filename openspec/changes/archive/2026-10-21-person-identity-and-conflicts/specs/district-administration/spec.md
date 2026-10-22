## MODIFIED Requirements

### Requirement: Districts and congregations
Only superadmins SHALL create districts; `DISTRICT_ADMIN` SHALL update a district and create congregations; `DISTRICT_ADMIN` or the congregation's `CONGREGATION_ADMIN` SHALL update a congregation; `VIEWER` SHALL list congregations. A district MAY carry a German `state_code` used for holiday import. District names SHALL be unique system-wide and congregation names unique within their district, compared case-, whitespace- and compatibility-insensitively; creating or renaming to a taken name SHALL fail with HTTP 409.

#### Scenario: District admin creates a district
- **WHEN** a non-superadmin posts to `/api/v1/districts`
- **THEN** the API responds with 403

#### Scenario: Duplicate congregation name
- **WHEN** a congregation is created or renamed to a name another congregation of the district already has, ignoring case and extra whitespace
- **THEN** the API responds with 409 and nothing is changed

#### Scenario: Same name in another district
- **WHEN** a congregation uses a name that only exists in a different district
- **THEN** it is accepted

#### Scenario: Existing duplicates
- **WHEN** duplicates already exist
- **THEN** they stay untouched and other edits of those rows are not blocked

### Requirement: Service leaders
Leaders SHALL be managed under `/api/v1/districts/{id}/leaders` (`VIEWER` read, `PLANNER` write). An authenticated member SHALL be able to link, inspect and remove the link of their own user account to a leader record via `/link-self`. Creating a leader whose normalised name (case, spacing, accents and leading honorifics or ranks ignored) matches an existing leader of the district, active or not, SHALL be rejected with HTTP 409 and code `LEADER_DUPLICATE` unless the request sets `confirm_duplicate`; the response lists the matches without contact data.

#### Scenario: Viewer creates a leader
- **WHEN** a viewer posts a new leader
- **THEN** the API responds with 403

#### Scenario: Same-named leader
- **WHEN** a planner creates a leader whose normalised name already exists in the district
- **THEN** the API responds with 409 `LEADER_DUPLICATE` listing id, name, congregation and active state of the matches
- **AND** nothing is saved until the request is repeated with `confirm_duplicate`

#### Scenario: Namesake confirmed
- **WHEN** the same request is repeated with `confirm_duplicate`
- **THEN** a separate leader record is created

## ADDED Requirements

### Requirement: Leader assignments
A leader SHALL have one or more assignments, each naming a congregation (or the district level), an optional role (congregation leader on a congregation, district leader on the district level) and a home flag, with exactly one home assignment. A leader SHALL be visible to planners of every assigned congregation. District-level planners SHALL manage all assignments; a congregation-scoped planner SHALL manage only the assignment of their own congregation.

#### Scenario: Leader of two congregations
- **WHEN** a person is assigned to congregations A and B, as congregation leader in both
- **THEN** the leader overview shows the person under A and under B with that role and marks the home congregation

#### Scenario: Congregation planner edits another congregation's assignment
- **WHEN** a planner of congregation A changes or removes the assignment of the same person for congregation B
- **THEN** the API responds with 403 and nothing is changed

#### Scenario: Role on the wrong level
- **WHEN** a request gives the congregation-leader role to a district-level assignment, or the district-leader role to a congregation assignment
- **THEN** the API rejects it with 422 (registration, approval, create and assignment changes alike)

#### Scenario: Last or home assignment
- **WHEN** the last assignment, or the home assignment while others exist, is removed
- **THEN** the API rejects the request until another assignment became the home assignment

