## ADDED Requirements

### Requirement: Application service imports SHALL be checked for unused imports
Backend CI SHALL run the pinned Ruff F401 rule independently of the project's global F401 ignore against every Python file under `app/application`. Existing F401 coverage of the registration router, domain models, domain ports, planning and domain services SHALL remain enforced.

#### Scenario: Current and newly added application modules use every import
- **WHEN** CI checks the `app/application` tree with isolated Ruff F401 and no imports are unused
- **THEN** the unused-import gate succeeds and maintains the previous scope

#### Scenario: An application workflow introduces an unused import
- **WHEN** a developer adds an unused import to an existing or newly created application module
- **THEN** CI rejects that change with F401, even if the global configuration ignores F401

#### Scenario: Functional exception behavior remains unchanged
- **WHEN** CSRF token validation or holiday-service operations encounter their existing error conditions
- **THEN** their existing runtime validation and exception behavior is unchanged by import-only cleanup
