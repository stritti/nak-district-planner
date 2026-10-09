## 1. Stack

- [x] 1.1 `docker-compose.prod.yml` with Traefik, Keycloak (+ database) and GHCR images pinned by `APP_VERSION`
- [x] 1.2 File-provider routes with admin allowlist and HSTS (`deploy/traefik/dynamic/routes.yml`), no Docker socket
- [x] 1.3 Network segmentation (`edge`, `app`, internal `data`/`idp`) with fixed proxy subnets
- [x] 1.4 Secret split and example files (`.env.keycloak*`), `.gitignore`

## 2. Verification

- [x] 2.1 Static tests for the invariants (`test_production_compose.py`) incl. negative check
- [x] 2.2 CI validates the production Compose configuration
- [x] 2.3 Local end-to-end run: all services healthy with `APP_ENV=production`, HTTP→HTTPS, HSTS/CSP, admin 403 outside the allowlist, issuer `https://<AUTH_HOST>/realms/<realm>`, spoofed `X-Forwarded-For` ignored

## 3. Documentation

- [x] 3.1 Operator guide `docs/production-compose.md`, links from runbook, documentation map, README and docs sidebar
