## 1. Stack

- [x] 1.1 `docker-compose.prod.yml` with Traefik, Keycloak (+ database) and GHCR images pinned by `APP_VERSION`
- [x] 1.2 File-provider routes with admin allowlist and HSTS (`deploy/traefik/dynamic/app.yml`, `keycloak.yml`), no Docker socket
- [x] 1.3 Network segmentation (`edge`, `app`, internal `data`/`idp`) with fixed proxy subnets
- [x] 1.4 Secret split and example files (`.env.keycloak*`), `.gitignore`
- [x] 1.5 Overrides for an existing Traefik or Keycloak (`deploy/compose/existing-traefik.yml`, `existing-keycloak.yml`); admin allowlist closed by default

## 2. Verification

- [x] 2.1 Static tests for the invariants (`test_production_compose.py`) incl. negative check
- [x] 2.2 CI validates the production Compose configuration, alone and with each override
- [x] 2.4 Local run of both overrides: app and admin allowlist via an external label-based Traefik, bundled Keycloak not started with `existing-keycloak.yml`
- [x] 2.3 Local end-to-end run: all services healthy with `APP_ENV=production`, HTTP→HTTPS, HSTS/CSP, admin 403 outside the allowlist, issuer `https://<AUTH_HOST>/realms/<realm>`, spoofed `X-Forwarded-For` ignored

## 3. Documentation

- [x] 3.1 Operator guide `docs/production-compose.md`, links from runbook, documentation map, README and docs sidebar
- [x] 3.2 Guide section for integrating an existing Traefik or Keycloak
- [x] 3.3 Bootstrap order (Keycloak before the application), backup and restore of the Keycloak database, complete IdP-provisioning settings
- [x] 3.4 `scripts/backup.sh` reads `BACKUP_ENCRYPT_KEY` from `.env`; `db` no longer loads `.env` (application secrets)
