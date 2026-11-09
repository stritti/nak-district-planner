## ADDED Requirements

### Requirement: Related routine dependency updates are grouped
Dependabot SHALL group patch/minor version updates separately for GitHub Actions, frontend runtime, frontend build, frontend testing, frontend linting, documentation, backend API, backend database, backend telemetry, backend tooling and remaining backend runtime dependencies. Each dependency SHALL match at most one group in its ecosystem and directory.

#### Scenario: Coupled frontend packages
- **WHEN** patch/minor updates exist for Vitest and its coverage provider
- **THEN** they are eligible for the same frontend testing pull request

#### Scenario: Runtime and tooling updates
- **WHEN** patch/minor updates exist for Vue, Vite and ESLint
- **THEN** they are eligible for separate frontend runtime, build and linting pull requests

#### Scenario: Backend families
- **WHEN** patch/minor updates exist for FastAPI and Starlette, SQLAlchemy and Alembic, or OpenTelemetry packages
- **THEN** each family is eligible for its own API, database or telemetry pull request
- **AND** the remaining-runtime group excludes all specialized families and test/lint tooling

#### Scenario: Documentation dependencies
- **WHEN** patch/minor documentation-toolchain updates are available at the repository root
- **THEN** they are eligible for a single documentation pull request separate from frontend updates

### Requirement: Major upgrades and security updates retain separate handling
New Dependabot groups SHALL apply only to version updates at patch/minor level. Major upgrades SHALL remain individual updates except for the existing CodeQL action group, which SHALL keep all CodeQL action references coupled across version levels. Existing security-update behavior SHALL be preserved.

#### Scenario: Major version update
- **WHEN** a major Vue, pytest or non-CodeQL action update is available
- **THEN** none of the new routine groups matches that update
- **AND** the update remains eligible for an individual pull request

#### Scenario: CodeQL coupling
- **WHEN** CodeQL init and analyze action references have a version update, including a major update
- **THEN** the existing CodeQL action group matches both references
- **AND** the general GitHub Actions group excludes CodeQL references

#### Scenario: Security update
- **WHEN** Dependabot identifies a vulnerable dependency
- **THEN** none of the new version-update groups applies to its security update
- **AND** existing security-update handling remains in effect

#### Scenario: New unmatched frontend package
- **WHEN** a new frontend dependency does not match a configured group
- **THEN** its version updates remain eligible for individual pull requests

### Requirement: Existing update coverage and container constraints are preserved
Dependabot SHALL retain all existing ecosystem/directory pairs and weekly schedules. Docker and Docker Compose updates SHALL remain individually reviewable, and the backend Python image SHALL retain its major/minor ignore rule.

#### Scenario: Container update
- **WHEN** a frontend base image or Compose service image has an available update
- **THEN** it remains outside the new groups and keeps the existing weekly schedule

#### Scenario: Backend Python minor or major release
- **WHEN** a newer Python minor or major image version is available
- **THEN** the existing ignore rule continues to exclude it
- **AND** compatible patch updates remain eligible
