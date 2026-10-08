## MODIFIED Requirements

### Requirement: Container builds are reproducible
Production container builds SHALL install application dependencies from locked dependency graphs and SHALL use explicitly versioned runtime and build-tool images. Runtime major/minor upgrades SHALL be reviewed separately from pinning changes.

#### Scenario: Frontend image is built
- **WHEN** the frontend Docker image installs JavaScript dependencies
- **THEN** Bun uses the committed lockfile in frozen mode

#### Scenario: Pinned container dependency is updated
- **WHEN** a newer supported base image or build tool is available
- **THEN** automated dependency monitoring opens a reviewable update instead of relying on a mutable tag

#### Scenario: CI verifies the shipped toolchain
- **WHEN** CI runs backend, migration, audit or frontend jobs
- **THEN** it uses the same Python and Bun versions as the production Dockerfiles
- **AND** a runtime image update is merged only together with the matching CI pins, `requires-python`, ruff `target-version` and lockfiles

### Requirement: Internal HTTP cannot bypass the public TLS boundary
The default production Compose configuration SHALL NOT publish the internal HTTP frontend service on all host interfaces. Public traffic SHALL enter through the configured TLS reverse proxy.

#### Scenario: Default Compose stack starts
- **WHEN** the frontend nginx is published to the host
- **THEN** it is bound to the loopback interface only
- **AND** direct HTTP access via the server's public interface is not provided by Compose

### Requirement: Browser security headers are applied
The application nginx SHALL emit a restrictive Content-Security-Policy and baseline browser security headers. Browser API connections SHALL be restricted to the application origin unless an explicitly reviewed external endpoint is required. HSTS SHALL be configured at the public TLS termination layer, not on the internal HTTP hop.

### Requirement: Shipped JavaScript dependency graph has no known high advisories
The release SHALL NOT ship a frontend dependency graph with known high or critical advisories. Remediation SHALL update the affected locked package to a patched compatible version in every committed Bun lockfile that contains it, without audit exceptions or a lowered audit threshold.

#### Scenario: Advisory in a transitive package
- **WHEN** `bun audit --audit-level=moderate` reports an advisory for a transitive package in `services/frontend/bun.lock`
- **THEN** the locked version is raised to the patched release in all Bun lockfiles that pin it
- **AND** `bun install --frozen-lockfile`, frontend tests and build pass unchanged
