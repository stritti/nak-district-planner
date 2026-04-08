## ADDED Requirements

### Requirement: Registration approval SHALL activate user access explicitly
The system SHALL treat self-registration and access activation as separate steps. A registered user MUST NOT gain access to protected business endpoints until a district administrator approves the registration and assigns an authorization scope.

#### Scenario: Registered but not approved user logs in
- **WHEN** a user authenticates successfully via OIDC but has no approved access assignment
- **THEN** protected business endpoints return `403 Forbidden`
- **AND** the response indicates that approval is pending

#### Scenario: District admin approves registration
- **WHEN** a district admin approves a pending registration
- **THEN** the registration status changes to `APPROVED`
- **AND** approval metadata (`approved_by_sub`, `approved_at`) is stored

### Requirement: Approval SHALL include role and scope assignment
The system SHALL require explicit authorization assignment during approval. Approval payload MUST include `role`, `scope_type`, and `scope_id`.

#### Scenario: Approval request missing assignment fields
- **WHEN** admin submits approval without one or more required assignment fields
- **THEN** system rejects the request with `422 Unprocessable Entity`

#### Scenario: Approval creates effective membership
- **WHEN** admin approves with valid `role`, `scope_type`, and `scope_id`
- **THEN** system creates or updates a membership for the approved user
- **AND** future authorization checks use that membership for access decisions

### Requirement: Registration user linkage SHALL be secure
If a bearer token is provided in the self-registration request, the system MUST validate it before using its `sub` claim for user linkage.

#### Scenario: Valid token links registration to subject
- **WHEN** registration request includes a valid bearer token
- **THEN** system validates token via configured OIDC validation flow
- **AND** stores token `sub` as registration `user_sub`

#### Scenario: Invalid token is rejected
- **WHEN** registration request includes an invalid or expired bearer token
- **THEN** system rejects the request with `401 Unauthorized`

#### Scenario: Registration without token remains possible
- **WHEN** registration request is sent without bearer token
- **THEN** system accepts registration as pending
- **AND** `user_sub` remains unset until later secure linkage
