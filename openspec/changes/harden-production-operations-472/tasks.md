## 1. Build and frontend runtime
- [x] 1.1 Add frontend and backend Docker ignore rules
- [x] 1.2 Pin unprivileged frontend Nginx and update all proxy paths to port 8080
- [x] 1.3 Preserve security headers, disable server tokens, and avoid caching app shell/service worker

## 2. Compose and secrets
- [x] 2.1 Add application runtime isolation, limits, service healthchecks
- [x] 2.2 Enforce Valkey auth in development and production Compose and application URL
- [x] 2.3 Validate production runtime credentials and standalone IdP secrets/HTTPS

## 3. Restore and documentation
- [x] 3.1 Back up encrypted database and global roles separately
- [x] 3.2 Migrate drill source and verify restored data, grants, RLS and definer functions
- [x] 3.3 Document configuration changes, role restore order and retained CSP decisions

## 4. Verification
- [ ] 4.1 Validate Compose interpolation and YAML schemas
- [ ] 4.2 Run regression and config tests (coverage >80%)
- [ ] 4.3 Run full Docker-based encrypted Restore Drill and review CI checks
