## ADDED Requirements

### Requirement: API schema unused imports SHALL be rejected independently of global Ruff ignores
The backend CI SHALL run Ruff F401 against all Python modules, including future modules, in `app/adapters/api/schemas` using an isolated invocation. Existing checked registration router, domain, `app/application` and integration-adapter paths SHALL remain covered.

#### Scenario: API schemas contain no unused imports
- **WHEN** CI runs the isolated F401 rule on the entire API schema directory
- **THEN** the unused-import gate succeeds

#### Scenario: An unused import is introduced in a schema
- **WHEN** a schema gains an unused import while the repository-wide F401 ignore remains
- **THEN** the isolated F401 gate fails regardless of the global ignore

#### Scenario: Pydantic schema behavior remains intact
- **WHEN** API tests exercise valid payload serialization and invalid request validation
- **THEN** the schema response and exception contracts remain unchanged by this CI-only scope expansion
