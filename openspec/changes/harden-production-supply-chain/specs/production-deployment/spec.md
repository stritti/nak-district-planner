## MODIFIED Requirements

### Requirement: Container builds are reproducible
Production container builds SHALL install application dependencies from locked dependency graphs and SHALL use explicitly versioned build tool images.

#### Scenario: Frontend image is built
- **WHEN** the frontend Docker image installs JavaScript dependencies
- **THEN** Bun uses the committed lockfile in frozen mode

### Requirement: Internal HTTP cannot bypass the public TLS boundary
The default production Compose configuration SHALL NOT publish the internal HTTP frontend service on all host interfaces. Public traffic SHALL enter through the configured TLS reverse proxy.

#### Scenario: Default Compose stack starts
- **WHEN** the frontend nginx is published to the host
- **THEN** it is bound to the loopback interface only
- **AND** direct HTTP access via the server's public interface is not provided by Compose

### Requirement: Browser security headers are applied
The application nginx SHALL emit a restrictive Content-Security-Policy and baseline browser security headers. HSTS SHALL be configured at the public TLS termination layer, not on the internal HTTP hop.