## ADDED Requirements

### Requirement: Keycloak provisioning access SHALL exclude authorization changes
When Keycloak provisioning is configured with the documented setup, the provisioning service account SHALL be able to search users, create users and trigger required-action emails in the application realm, and MUST NOT be able to map roles, change group memberships, impersonate users, delegate permissions or delete users. The service account MUST NOT hold `realm-management` client roles that bypass fine-grained permission evaluation.

#### Scenario: Provisioning operations are permitted
- **WHEN** the service account searches a user by email, creates a user and triggers `VERIFY_EMAIL` and `UPDATE_PASSWORD`
- **THEN** Keycloak accepts each request

#### Scenario: Role mapping is denied
- **WHEN** the service account tries to add a realm or client role mapping to any user
- **THEN** Keycloak rejects the request with `403 Forbidden`

#### Scenario: Group membership change is denied
- **WHEN** the service account tries to add a user to a group
- **THEN** Keycloak rejects the request with `403 Forbidden`

#### Scenario: User deletion is denied
- **WHEN** the service account tries to delete a user
- **THEN** Keycloak rejects the request with `403 Forbidden`

#### Scenario: Legacy roles are removed
- **WHEN** the setup script runs against a realm whose provisioning service account still holds `manage-users` or `view-users`
- **THEN** those role mappings are removed after the fine-grained permissions are in place
