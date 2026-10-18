## ADDED Requirements

### Requirement: Docker-specific application settings are loaded from env files
The Docker Compose application SHALL load container-specific backend and worker runtime overrides from a dedicated env file instead of duplicating active `environment` blocks in Compose YAML.

#### Scenario: Backend and worker start in Docker Compose
- **WHEN** Docker Compose resolves the `backend` or `worker` service
- **THEN** the service SHALL load `.env` followed by `.env.docker`
- **AND** `DATABASE_URL` SHALL target the `db` service
- **AND** `VALKEY_URL` SHALL target the `valkey` service

### Requirement: Migration credentials remain isolated
The migration-only owner database URL SHALL be defined outside the shared application Docker env file and SHALL be loaded only by the `migrate` service.

#### Scenario: Long-running application services are configured
- **WHEN** Docker Compose resolves `backend` and `worker`
- **THEN** their Docker-specific env file SHALL NOT define `MIGRATION_DATABASE_URL`
- **AND** the migration override SHALL NOT be loaded by either service

#### Scenario: Database migration is executed
- **WHEN** the `migrate` service is run
- **THEN** it SHALL load `.env.docker.migrate`
- **AND** `MIGRATION_DATABASE_URL` SHALL use the PostgreSQL owner credentials and Docker-internal `db` hostname

### Requirement: Test database configuration is isolated
The PostgreSQL test service SHALL receive its test database name through a dedicated env-file override.

#### Scenario: Test database starts
- **WHEN** Docker Compose resolves `db-test`
- **THEN** `.env.docker.test` SHALL override `POSTGRES_DB` with `nak_planner_test`
- **AND** the main `db` service SHALL continue using the database name from `.env`

### Requirement: Missing required database inputs fail during Compose interpolation
Docker-specific connection strings SHALL mark required database inputs as mandatory Compose interpolation values.

#### Scenario: Required database credential is absent
- **WHEN** Docker Compose evaluates a Docker env file without a required application or PostgreSQL credential
- **THEN** interpolation SHALL fail with a descriptive required-variable message before the affected container starts
