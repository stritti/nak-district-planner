## ADDED Requirements

### Requirement: Consistent error texts for failed requests
The SPA SHALL show the same German text per failure kind in views, dialogs and error toasts: the server's text (`detail` or `detail.message`) for 400, 404, 409 and 422, otherwise a fixed text per status, for an expired session and for an unreachable server. It MUST NOT show the raw status line, the response body, a 403 detail or a 5xx detail. Error texts SHALL use `role="alert"`.

#### Scenario: Taken name
- **WHEN** creating a congregation fails with 409 and the detail "Eine Gemeinde mit diesem Namen existiert bereits"
- **THEN** the dialog shows exactly that text

#### Scenario: Missing permission
- **WHEN** a request fails with 403, whatever its detail
- **THEN** the SPA shows "Für diese Aktion fehlt die Berechtigung."

#### Scenario: Server failure
- **WHEN** a request fails with a 5xx status
- **THEN** the SPA shows a request to try again later and none of the response body

### Requirement: Onboarding empty states
Empty lists that a new installation starts with SHALL explain the next step and, for users allowed to take it, offer it as an action: the first district, the first congregation of a district, and the matrix of a district without congregations. The matrix SHALL distinguish a district without congregations from a congregation or group filter without matches.

#### Scenario: District without congregations in the matrix
- **WHEN** the matrix of a district without congregations is shown and no congregation filter is set
- **THEN** it states that the district has no congregations yet instead of a filter hint
- **AND** offers "Gemeinde anlegen" only to district admins

#### Scenario: Group without congregations
- **WHEN** the selected group of the matrix has no congregations
- **THEN** it states that the group has no congregations and offers to show all groups
