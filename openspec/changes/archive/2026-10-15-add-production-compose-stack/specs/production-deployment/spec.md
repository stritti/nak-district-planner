## ADDED Requirements

### Requirement: Production stack runs released images behind Traefik and Keycloak
The repository SHALL provide a production Compose stack that runs the application from published release images pinned by version, terminates TLS at Traefik with automatic certificates, provides Keycloak as OIDC provider, and preserves the deployment boundaries of the development stack.

#### Scenario: Deployment pulls a released version
- **WHEN** an operator sets `APP_VERSION` to a released version and starts the production stack
- **THEN** backend, worker, beat, migrate and frontend run the GHCR images of that version, nothing is built on the server, and Compose refuses to start without `APP_VERSION`

#### Scenario: Only the TLS proxy is public
- **WHEN** the production stack is running
- **THEN** only Traefik publishes ports (80 redirecting to 443), no container mounts the Docker socket, and databases and cache are attached only to internal networks

#### Scenario: Keycloak administration is restricted
- **WHEN** a client outside `KEYCLOAK_ADMIN_ALLOWED_IPS` requests `/admin` or the `master` realm on the auth host
- **THEN** Traefik answers 403, while the application realm stays publicly reachable

#### Scenario: Secrets stay with their consumers
- **WHEN** the production stack starts
- **THEN** the application database owner password reaches only `db` and `migrate`, the Keycloak admin and database credentials reach only `keycloak` and `keycloak-db`, and runtime services still wait for the one-shot migration

#### Scenario: Forwarded headers are trusted only from the proxy hop
- **WHEN** a client sends its own `X-Forwarded-For` header
- **THEN** neither the audit log nor rate limiting use it, and Keycloak derives scheme and host only from headers sent by the proxy network

#### Scenario: Admin allowlist is closed by default
- **WHEN** `KEYCLOAK_ADMIN_ALLOWED_IPS` is not set
- **THEN** the Keycloak administration is reachable only from the server itself (`127.0.0.1/32`)

#### Scenario: Existing Traefik on the host
- **WHEN** the operator adds `deploy/compose/existing-traefik.yml`
- **THEN** the bundled Traefik does not start, frontend and Keycloak join the operator's external proxy network and publish their routes, the admin allowlist and HSTS through labels, and still no container of the stack publishes ports or mounts the Docker socket

#### Scenario: Existing Keycloak on the host
- **WHEN** the operator adds `deploy/compose/existing-keycloak.yml`
- **THEN** the bundled Keycloak and its database do not start, the bundled Traefik serves no Keycloak routes, and the auth host is no longer aliased to Traefik inside the stack
