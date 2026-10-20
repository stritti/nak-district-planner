## ADDED Requirements

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
