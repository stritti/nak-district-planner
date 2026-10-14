## ADDED Requirements

### Requirement: Environment backup files are never tracked
The security CI SHALL reject tracked environment backup files named `.env.bak`, `.env.<variant>.bak`, or `<name>.env.bak` without printing their contents. Git ignore rules SHALL prevent accidental staging of these backups.

#### Scenario: A Keycloak environment backup is committed
- **WHEN** a pull request adds a tracked `idp-deploy/keycloak/.env.bak`
- **THEN** the required security audit job fails before dependency auditing
- **AND** no credential values are included in the error message

#### Scenario: No environment backups are tracked
- **WHEN** only intentionally committed example configuration files exist
- **THEN** the security audit proceeds normally
