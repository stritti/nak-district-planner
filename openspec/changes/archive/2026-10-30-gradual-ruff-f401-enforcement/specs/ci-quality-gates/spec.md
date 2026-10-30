## ADDED Requirements

### Requirement: Production Python modules SHALL incrementally enforce unused-import checks
The backend CI SHALL run an explicitly selected Ruff F401 check against the registration domain model and registration API router even while F401 is globally ignored for legacy modules. The check MUST reject newly introduced unused imports in these reviewed files.

#### Scenario: Reviewed registration modules contain only used imports
- **WHEN** the backend CI analyzes both reviewed registration files
- **THEN** the isolated F401 check succeeds

#### Scenario: Unused import is added to a protected registration module
- **WHEN** an unused import is added to either protected file
- **THEN** the dedicated F401 check fails instead of inheriting the global ignore
