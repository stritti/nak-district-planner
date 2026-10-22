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
- **WHEN** the service account tries to set or remove a password credential of any user, through the reset-password endpoint, a user update carrying `credentials`, or the credential deletion endpoint
- **THEN** Keycloak rejects the request with `403 Forbidden` and the user's password is unchanged

#### Scenario: Delegation is denied
- **WHEN** a user authenticates and requests the scope `delegation:client:nak-planner-provisioning` for the provisioning client
- **THEN** the issued subject token contains neither that scope nor a `may_act` claim

#### Scenario: Conflicting permissions stop the setup
- **WHEN** the setup script finds Users permissions it did not create that target specific users, or that cover the `view`, `manage` or `reset-password` scope for all users, or Groups permissions covering `view-members` or `manage-members`, or finds `nak-planner-password-reset` assigned to anyone, or `nak-planner-provisioner` assigned to anyone but the service account or carrying composites, or a user storage provider with import disabled
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
- **THEN** it states that the `manage` scope required for user creation and required-action emails also allows deleting and editing users, including account takeover by changing a user's email before a required-action email, removing OTP or WebAuthn credentials, or linking an external identity, and it recommends alerting on admin events

#### Scenario: Legacy roles are removed
- **WHEN** the setup script runs against a realm whose provisioning service account still holds `realm-management` roles
- **THEN** those role mappings are removed after the fine-grained permissions are in place

#### Scenario: Inherited legacy roles stop the setup
- **WHEN** the service account still holds a `realm-management` role through a group or composite role after the direct mappings are removed
- **THEN** the setup script stops with an error naming the role and its source, and does not report success

#### Scenario: Unsupported Keycloak version
- **WHEN** the setup script runs against a Keycloak without fine-grained admin permissions v2
- **THEN** it stops with an error naming the minimum version 26.8.1 and changes no permissions
