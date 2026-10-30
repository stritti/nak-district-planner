## ADDED Requirements

### Requirement: Domain model unused imports SHALL be rejected in CI
The backend CI SHALL run Ruff F401 independently of the global F401 ignore against all Python files in `app/domain/models`. The gate MUST continue covering the registration API route and the complete `app/domain/ports`, `app/domain/planning` and `app/domain/services` directories introduced by earlier migration stages.

#### Scenario: All domain model modules have used imports
- **WHEN** the backend CI checks the domain model package with isolated Ruff F401
- **THEN** the check succeeds, and no previous coverage paths are dropped

#### Scenario: Unused import in a current or new domain model
- **WHEN** an unused Python import is introduced anywhere under `app/domain/models`
- **THEN** the CI F401 check fails even while the global ignore remains in effect

#### Scenario: Intentional package reexports remain usable
- **WHEN** consumers import documented symbols from `app.domain.models`
- **THEN** the package's explicit `__all__` reexports remain available and unchanged
