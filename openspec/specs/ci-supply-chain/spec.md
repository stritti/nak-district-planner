# ci-supply-chain Specification

## Purpose
Haertet die GitHub-Actions-Pipeline gegen Supply-Chain-Angriffe: unveraenderlich gepinnte Actions und minimale Token-Rechte je Job.

## Requirements

### Requirement: Workflow actions are pinned to immutable commits
Every action referenced by a GitHub Actions workflow SHALL be pinned to a full 40-character commit SHA. The human-readable release version SHALL be recorded as a trailing comment so that automated dependency updates can bump SHA and version together.

#### Scenario: Upstream tag is moved
- **WHEN** the maintainer of a referenced action re-points a release tag to a different commit
- **THEN** the workflows keep executing the previously reviewed commit
- **AND** the change only takes effect through a reviewable dependency-update pull request

### Requirement: Workflow token permissions follow least privilege
Workflows SHALL grant only read scopes by default. Write scopes SHALL be granted only to the jobs that need them.

#### Scenario: CI test jobs run on a pull request
- **WHEN** the frontend or E2E jobs of the CI workflow run
- **THEN** their token cannot write pull-request comments
- **AND** only the backend coverage job receives `pull-requests: write`

### Requirement: Environment backup files are never tracked
The security CI SHALL reject tracked environment backup files named `.env.bak`, `.env.<variant>.bak`, or `<name>.env.bak` without printing their contents. Git ignore rules SHALL prevent accidental staging of these backups.

#### Scenario: A Keycloak environment backup is committed
- **WHEN** a pull request adds a tracked `idp-deploy/keycloak/.env.bak`
- **THEN** the required security audit job fails before dependency auditing
- **AND** no credential values are included in the error message

#### Scenario: No environment backups are tracked
- **WHEN** only intentionally committed example configuration files exist
- **THEN** the security audit proceeds normally
