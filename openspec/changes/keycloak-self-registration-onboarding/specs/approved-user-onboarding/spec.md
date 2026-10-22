## ADDED Requirements

### Requirement: The backend SHALL hold no IdP administration credential
The backend MUST NOT create, modify or invite users in Keycloak and MUST NOT be configured with a Keycloak Admin API credential. When the former Keycloak provisioning provider is still configured, the application SHALL refuse to start.

#### Scenario: Keycloak provider still configured
- **WHEN** the application starts with `IDP_PROVISIONING_PROVIDER=keycloak` and provisioning enabled
- **THEN** startup is refused with a configuration error that names the setting and points to the upgrade note

#### Scenario: Approval without provisioning
- **WHEN** a district admin approves a registration and no provisioning provider is configured
- **THEN** the registration is approved and no request is sent to the IdP

#### Scenario: Provisioning client removed by setup
- **WHEN** the realm setup script runs against a realm that contains the client `nak-planner-provisioning`
- **THEN** the script deletes that client and creates no client with a service account

### Requirement: User accounts SHALL be created by self-registration with a verified email
The documented realm setup SHALL allow users to register themselves in the application realm only with email verification and the email address as username. Access to protected business endpoints SHALL still require an approved registration linked by `sub` or by a verified email claim.

#### Scenario: Realm allows verified self-registration
- **WHEN** the realm setup script runs
- **THEN** the realm has `registrationAllowed`, `verifyEmail` and `registrationEmailAsUsername` enabled

#### Scenario: Self-registered account without approval
- **WHEN** a user registers in Keycloak, verifies the email and logs in without an approved registration
- **THEN** protected business endpoints return `403 Forbidden` indicating that approval is pending

#### Scenario: Approved registration linked on first login
- **WHEN** a registration for an email is approved and the user later logs in with a token whose `email` matches and `email_verified` is `true`
- **THEN** the user receives the approved membership

#### Scenario: Registration page offers account creation
- **WHEN** an unauthenticated user submits the registration form
- **THEN** the page offers to create an account, which starts the OIDC login with `prompt=create`, and states that the account email must match the registration email

#### Scenario: Authenticated user registers
- **WHEN** an authenticated user submits the registration form
- **THEN** the request carries the user's access token and the registration stores the token's `sub`

## REMOVED Requirements

### Requirement: Keycloak provisioning SHALL use a least-privilege service account
**Reason**: The backend no longer provisions Keycloak users; any Admin API credential with the `manage` scope allows account takeover (see `keycloak-self-registration-onboarding/design.md`).
**Migration**: Remove `IDP_PROVISIONING_PROVIDER=keycloak` and all `IDP_PROVISIONING_KEYCLOAK_*` settings and rerun the realm setup script, which deletes the provisioning client.

### Requirement: Invitation links SHALL be time-limited and return to the application
**Reason**: The backend no longer sends invitations; users create and verify their account themselves.
**Migration**: None; invitations already sent stay valid until their lifetime ends.
