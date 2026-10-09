## Why

Production operators had to assemble the stack themselves: `docker-compose.yml` builds the images on the server and expects an external TLS proxy, and the Keycloak example in `idp-deploy/` uses a hard-coded host, default passwords, insecure cookies and the Docker provider of Traefik. A release should be deployable from the published GHCR images with TLS and an identity provider out of the box, without weakening the existing deployment boundaries (owner credentials, migration gate, no Docker socket, no public bypass of TLS).

## What Changes

- New `docker-compose.prod.yml`: Traefik (Let's Encrypt, HTTP→HTTPS, HSTS), Keycloak with its own PostgreSQL, and the application from `ghcr.io/stritti/nak-district-planner/{backend,frontend}:${APP_VERSION}`; nothing is built on the server.
- Traefik routes come from a file provider (`deploy/traefik/dynamic/app.yml` and `keycloak.yml`, Go templates over `APP_HOST`, `AUTH_HOST`, `KEYCLOAK_ADMIN_ALLOWED_IPS`); no container mounts the Docker socket.
- Keycloak administration (`/admin`, realm `master`) is reachable only from an IP allowlist.
- Network segmentation: `edge` (proxy hop, fixed subnet trusted by nginx and Keycloak), `app`, internal `data` and `idp`. Inside the stack the auth host resolves to Traefik, so token validation does not hairpin through the internet.
- Secrets split by need-to-know: `.env.db` (db, migrate), `.env.keycloak` (keycloak), `.env.keycloak-db` (keycloak-db); new example files and `.gitignore` entries.
- Optional overrides in `deploy/compose/` for hosts that already run Traefik (`existing-traefik.yml`: routes via Docker labels on the operator's Traefik, bundled Traefik disabled) or Keycloak (`existing-keycloak.yml`: bundled Keycloak and its routes disabled, auth host resolved via DNS).
- CI validates the production Compose configuration; static tests guard the invariants; operator guide `docs/production-compose.md`.

## Impact

- Affected specs: `production-deployment` (ADDED requirement).
- Affected files: `docker-compose.prod.yml`, `deploy/traefik/dynamic/{app,keycloak}.yml`, `deploy/compose/existing-{traefik,keycloak}.yml`, `.env.example`, `.env.keycloak.example`, `.env.keycloak-db.example`, `.gitignore`, `scripts/backup.sh`, `.github/workflows/build.yml`, `services/backend/tests/unit/test_production_compose.py`, docs.
- No application code changes; `docker-compose.yml` for development is unchanged.
