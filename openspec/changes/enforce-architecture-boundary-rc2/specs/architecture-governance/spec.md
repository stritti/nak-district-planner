## ADDED Requirements

### Requirement: Application dependency direction is enforced
The backend SHALL prevent new modules below `app.application` from depending directly on concrete modules below `app.adapters`.

Existing RC-2 violations MAY remain temporarily only when they are named in an explicit legacy allowlist with a rationale. The allowlist SHALL be treated as technical debt and SHALL NOT be expanded for new application services.

#### Scenario: New application service uses a domain port
- **WHEN** a new application service requires persistence, messaging, mail, identity-provider, or other infrastructure behavior
- **THEN** it depends on a port/interface owned by the domain or application boundary
- **AND** a concrete adapter is supplied at a composition boundary
- **AND** the architecture check passes without adding the new service to the legacy allowlist

#### Scenario: New application service imports a concrete adapter
- **WHEN** a module not present in the RC-2 legacy allowlist imports `app.adapters...`
- **THEN** the architecture check fails
- **AND** the dependency must be inverted instead of allowlisted

#### Scenario: Legacy debt is removed
- **WHEN** an allowlisted application module no longer requires a concrete adapter
- **THEN** its legacy allowlist entry is removed in the same change

### Requirement: Runtime version metadata has one source of truth
The FastAPI application SHALL expose the same package-derived application version as health and system version reporting.

#### Scenario: Application starts from an installed package
- **WHEN** the backend application is created
- **THEN** `app.version` equals `settings.app_version`
- **AND** no independent hard-coded API version is used
