## ADDED Requirements

### Requirement: Keycloak provisioning access SHALL exclude authorization changes
When Keycloak provisioning is configured with the documented setup (Keycloak 26.2 or newer), the provisioning service account SHALL be able to search users, create users and trigger required-action emails in the application realm, and MUST NOT be able to reset passwords, map roles, change group memberships, impersonate users or delegate permissions. The service account MUST NOT hold `realm-management` client roles.

#### Scenario: Provisioning operations are permitted
- **WHEN** the service account searches a user by email, creates a user and triggers `VERIFY_EMAIL` and `UPDATE_PASSWORD`
- **THEN** Keycloak accepts each request

#### Scenario: Role mapping is denied
- **WHEN** the service account tries to add a realm or client role mapping to any user
- **THEN** Keycloak rejects the request with `403 Forbidden`

#### Scenario: Password reset is denied
- **WHEN** the service account tries to set a password for any user
- **THEN** Keycloak rejects the request with `403 Forbidden`

#### Scenario: Delegation is denied
- **WHEN** the service account tries to create or change an admin permission or policy
- **THEN** Keycloak rejects the request with `403 Forbidden`

#### Scenario: Conflicting user-specific permissions stop the setup
- **WHEN** the setup script finds existing Users permissions that target specific users in the application realm
- **THEN** it stops with an error naming them, before removing any legacy roles

#### Scenario: Group membership change is denied
- **WHEN** the service account tries to add a user to a group
- **THEN** Keycloak rejects the request with `403 Forbidden`

#### Scenario: Impersonation is denied
- **WHEN** the service account tries to impersonate a user
- **THEN** Keycloak rejects the request with `403 Forbidden`

#### Scenario: Deletion remains a documented residual risk
- **WHEN** an operator reads the provisioning documentation
- **THEN** it states that the `manage` scope required for user creation and required-action emails also allows deleting and editing users, and recommends enabling Keycloak admin events

#### Scenario: Legacy roles are removed
- **WHEN** the setup script runs against a realm whose provisioning service account still holds `realm-management` roles
- **THEN** those role mappings are removed after the fine-grained permissions are in place

#### Scenario: Unsupported Keycloak version
- **WHEN** the setup script runs against a Keycloak without fine-grained admin permissions v2
- **THEN** it stops with an error naming the minimum version 26.2 and changes no permissions
