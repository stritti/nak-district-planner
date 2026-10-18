# Design: Docker Compose env-file layering

## Context

The project supports two execution modes from the same checkout:

1. Host-local backend execution, where `DATABASE_URL` and `VALKEY_URL` point to localhost.
2. Docker Compose execution, where the same settings must point to the Compose service names `db` and `valkey`.

Previously, Docker-specific values were repeated in active `environment` blocks in both the base and development override Compose files. The migration service additionally needs owner-level database credentials, and `db-test` needs a different database name.

## Decision

Use Docker Compose `env_file` layering:

- `.env` remains the user-managed source for secrets, credentials, and host-local defaults.
- `.env.docker` is committed and contains only shared Docker-internal backend/worker overrides. Its values are derived from `.env` through Compose interpolation.
- `.env.docker.migrate` is loaded only by `migrate` and derives `MIGRATION_DATABASE_URL` from the PostgreSQL owner credentials.
- `.env.docker.test` is loaded only by `db-test` and overrides `POSTGRES_DB` with the isolated test database name.

The Docker-specific files contain no literal secrets. Required database inputs use Compose's `${VAR:?message}` syntax so configuration fails before containers start when a required value is missing.

## Security boundary

The privileged `MIGRATION_DATABASE_URL` must not be part of `.env.docker`. Keeping it in a migration-only env file prevents the derived owner URL from being added to long-running backend and worker containers through the new shared Docker override.

This change intentionally does not redesign the pre-existing contents of the user-managed `.env`; it only removes Docker-specific duplication from Compose YAML.

## Compatibility

- Direct host execution keeps using the localhost values in `.env`.
- Normal development Compose automatically merges `docker-compose.override.yml`, but runtime environment values now come from the base Compose env-file declarations.
- Production Compose with `-f docker-compose.yml` uses the same env-file layering and therefore does not depend on the development override for correct internal networking.
- `db-test` continues using `nak_planner_test` without changing the main PostgreSQL database configuration.

## Verification

Focused unit tests inspect the Compose service blocks and env files without adding a YAML runtime dependency. They verify shared wiring, absence of active duplicated environment blocks, isolated migration credentials, the test database override, and required-variable interpolation guards.
