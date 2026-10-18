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
