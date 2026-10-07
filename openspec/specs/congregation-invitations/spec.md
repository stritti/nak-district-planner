# congregation-invitations Specification

## Purpose

Allows a host congregation to invite other congregations of the district (or record an external free-text target) to a service, creating linked event copies whose changes are only applied after confirmation.

## Requirements

### Requirement: Invitation targets
An invitation SHALL have exactly one target: `DISTRICT_CONGREGATION` with `target_congregation_id` or `EXTERNAL_NOTE` with `external_target_note`. Creating invitations (`POST` on an event) and deleting them SHALL require `PLANNER`; listing SHALL require `VIEWER`. Saving the same target for the same service again SHALL update the existing invitation instead of duplicating it.

#### Scenario: Both target fields set
- **WHEN** a request sets both `target_congregation_id` and `external_target_note`
- **THEN** it is rejected with a validation error

### Requirement: Linked invitation events
For each internal invitation the system SHALL create a linked slot in the target congregation referencing the source slot and source congregation. Leader assignment SHALL be maintained only on the host service; the invited congregation's matrix SHALL mirror the host's leader read-only and show the host congregation, and the host cell SHALL show the invitation count.

#### Scenario: Invited congregation opens the cell
- **WHEN** a user opens an invitation copy in the matrix
- **THEN** no local assignment editing is offered

### Requirement: Overwrite requests on source changes
Changes to date, time, location or description of a source service SHALL create `PENDING_OVERWRITE` requests for linked copies. `GET /api/v1/invitations/overwrite-requests` SHALL list them (`VIEWER`) and the decision endpoint SHALL apply (`ACCEPTED`) or discard (`REJECTED`) the proposed values for a `PLANNER`, storing the decision with a timestamp.

#### Scenario: Request rejected
- **WHEN** the invited congregation rejects an overwrite request
- **THEN** the linked copy keeps its values and the request is recorded as rejected
