## ADDED Requirements

### Requirement: Keycloak provisioning access SHALL exclude authorization changes
When Keycloak provisioning is configured with the documented setup (Keycloak 26.8.1 or newer), the provisioning service account SHALL be able to search users, create users and trigger required-action emails in the application realm, and MUST NOT be able to reset passwords, map roles, change group memberships, impersonate users or delegate permissions. The service account MUST NOT hold `realm-management` client roles.

#### Scenario: Provisioning operations are permitted
- **WHEN** the service account searches a user by email, creates a user and triggers `VERIFY_EMAIL` and `UPDATE_PASSWORD`
- **THEN** Keycloak accepts each request

#### Scenario: Role mapping is denied
- **WHEN** the service account tries to add a realm or client role mapping to any user
- **THEN** Keycloak rejects the request with `403 Forbidden`

#### Scenario: Password reset is denied
- **WHEN** the service account tries to set or remove credentials of any user, through the reset-password endpoint, a user update carrying `credentials`, or the credential deletion endpoint
- **THEN** Keycloak rejects the request with `403 Forbidden` and the user's credentials are unchanged

#### Scenario: Delegation is denied
- **WHEN** a token exchange requests delegation with the service account as actor
- **THEN** the issued token contains no delegation scope and no `may_act` claim, or the request is rejected

#### Scenario: Conflicting permissions stop the setup
- **WHEN** the setup script finds Users permissions it did not create that target specific users, or that cover the `view`, `manage` or `reset-password` scope for all users, or finds `nak-planner-password-reset` assigned to anyone, or a user storage provider with import disabled
- **THEN** it stops with an error naming them, before changing permissions or removing any legacy roles

#### Scenario: Provisioning works with restricted client scope
- **WHEN** the provisioning client has `Full Scope Allowed` disabled
- **THEN** the setup script maps `nak-planner-provisioner` into the client's role scope and provisioning operations are still permitted

#### Scenario: Group membership change is denied
- **WHEN** the service account tries to add a user to a group
- **THEN** Keycloak rejects the request with `403 Forbidden`

#### Scenario: Group injection on user creation is denied
- **WHEN** the service account creates a user whose request lists a group that maps an admin role
- **THEN** Keycloak rejects the request and neither the user nor the membership exists afterwards

#### Scenario: Impersonation is denied
- **WHEN** the service account tries to impersonate a user
- **THEN** Keycloak rejects the request with `403 Forbidden`

#### Scenario: Deletion remains a documented residual risk
- **WHEN** an operator reads the provisioning documentation
- **THEN** it states that the `manage` scope required for user creation and required-action emails also allows deleting and editing users, including changing a user's email and sending that address a required-action link, and it recommends OTP for privileged accounts and alerting on admin events

#### Scenario: Legacy roles are removed
- **WHEN** the setup script runs against a realm whose provisioning service account still holds `realm-management` roles
- **THEN** those role mappings are removed after the fine-grained permissions are in place

#### Scenario: Inherited legacy roles stop the setup
- **WHEN** the service account still holds a `realm-management` role through a group or composite role after the direct mappings are removed
- **THEN** the setup script stops with an error naming the role and its source, and does not report success

#### Scenario: Unsupported Keycloak version
- **WHEN** the setup script runs against a Keycloak without fine-grained admin permissions v2
- **THEN** it stops with an error naming the minimum version 26.8.1 and changes no permissions
