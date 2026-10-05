## MODIFIED Requirements

### Requirement: Database migrations run before runtime services
Schema-changing migrations SHALL execute as a dedicated one-shot deployment step with migration credentials. API and worker processes SHALL NOT execute Alembic upgrades during application startup. The API runtime SHALL fail fast when the deployed database revision does not match the Alembic head shipped with the application, without applying DDL itself.

#### Scenario: Normal stack startup
- **WHEN** the Compose stack is started
- **THEN** the migration service waits for a healthy database
- **AND** applies `alembic upgrade head`
- **AND** backend and worker start only after migration completion succeeds

#### Scenario: Migration fails
- **WHEN** the migration service exits unsuccessfully
- **THEN** backend and worker do not start

#### Scenario: Runtime starts against a stale schema
- **WHEN** the API process starts and `alembic_version` does not match the Alembic head shipped with the application
- **THEN** startup fails before request processing begins
- **AND** the runtime does not apply a migration automatically

#### Scenario: Schema version cannot be read
- **WHEN** the API process cannot read `alembic_version`
- **THEN** startup fails with a schema-version error
- **AND** operators are directed to run the deployment migration step

### Requirement: Runtime credentials cannot perform deployment DDL
Backend and worker SHALL load only runtime database credentials. Migration-owner credentials SHALL be scoped to the migration service.

### Requirement: Migration operations are documented
The repository SHALL document the explicit production and local-development migration commands, including the one-shot Compose service and the fail-fast runtime schema check.
