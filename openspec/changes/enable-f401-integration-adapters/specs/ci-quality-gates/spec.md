## ADDED Requirements

### Requirement: Integration-adapter unused imports SHALL fail CI
Backend CI SHALL check unused imports with Ruff F401 independently of the global project F401 ignore for all Python modules, including newly added files, in `app/adapters/auth`, `app/adapters/idp`, `app/adapters/mail`, `app/adapters/version_check`, `app/adapters/calendar`, and `app/adapters/worker`. Existing protected domain, registration and `app/application` scopes SHALL remain included.

#### Scenario: All adapter imports are used
- **WHEN** CI runs isolated Ruff F401 against the six adapter directories and no unused imports exist
- **THEN** the F401 gate succeeds

#### Scenario: An unused adapter import is introduced
- **WHEN** an existing or newly added adapter module contains an unused import
- **THEN** CI fails the isolated F401 gate regardless of the global ignore setting

#### Scenario: Failure paths in adapters remain unchanged
- **WHEN** a worker, mail, calendar or OIDC adapter experiences its existing failure condition
- **THEN** its prior error-handling behavior remains unchanged by the CI-only expansion
