# approved-user-onboarding Specification

## Purpose

Separates self-registration from access activation: a district administrator approves registrations with an explicit role and scope, optionally provisioning the user in the IdP.

## Requirements

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

### Requirement: Approval SHALL support optional IDP provisioning
When enabled by configuration, the system SHALL notify a provisioning endpoint at approval time so the user can be invited/created in the external IDP.

#### Scenario: Provisioning enabled and endpoint succeeds
- **WHEN** a registration is approved and provisioning is enabled
- **THEN** system calls the configured provisioning endpoint with registration and scope metadata
- **AND** stores provisioning status on the registration

#### Scenario: Provisioning endpoint fails
- **WHEN** provisioning is enabled and endpoint call fails
- **THEN** approval remains successful for internal authorization state
- **AND** registration stores provisioning error details for operators

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

### Requirement: Keycloak provisioning SHALL use a least-privilege service account
When the Keycloak provider is selected, the system SHALL authenticate against the Keycloak Admin API only with the OAuth 2.0 client credentials grant of a dedicated confidential client in the application realm. The system MUST NOT use a password grant or any account of the `master` realm. The client's service account SHALL need no permissions beyond managing and viewing users of the application realm. The client secret MUST NOT appear in logs, API responses or stored provisioning errors.

#### Scenario: Approval provisions via service account
- **WHEN** a registration is approved and Keycloak provisioning is enabled with client id and client secret
- **THEN** the system obtains a token from the application realm's token endpoint with `grant_type=client_credentials`
- **AND** no request is sent to the `master` realm

#### Scenario: Production start without client credentials
- **WHEN** the application starts in production with the Keycloak provider enabled and client id or client secret missing
- **THEN** startup is refused with a configuration error naming the missing setting

#### Scenario: Legacy admin credentials still configured
- **WHEN** the application starts in production with the Keycloak provider and the former admin username or admin password settings are present
- **THEN** startup is refused with a configuration error asking to remove them

#### Scenario: Token request rejected
- **WHEN** Keycloak rejects the client credentials
- **THEN** the approval still succeeds for internal authorization state
- **AND** the registration stores a provisioning error that contains the HTTP status but not the secret

### Requirement: Invitation links SHALL be time-limited and return to the application
When an invitation is sent on approval, the system SHALL request the required actions `VERIFY_EMAIL` and `UPDATE_PASSWORD` with an explicit link lifetime. The lifetime SHALL default to 72 hours and MUST be configurable only between 1 hour and 7 days. When a return URI is configured, the system SHALL pass the application's OIDC client id and that URI so the user returns to the application after completing the actions.

#### Scenario: Default lifetime
- **WHEN** an invitation is sent and no lifetime is configured
- **THEN** the invitation request carries a lifetime of 259200 seconds

#### Scenario: Lifetime outside allowed range
- **WHEN** the configured lifetime is below 3600 or above 604800 seconds
- **THEN** settings validation fails at startup

#### Scenario: Return URI configured
- **WHEN** an invitation is sent and a return URI is configured
- **THEN** the invitation request carries the application's OIDC client id and the configured return URI

#### Scenario: No return URI configured
- **WHEN** an invitation is sent without a configured return URI
- **THEN** the invitation request carries neither `client_id` nor `redirect_uri`
