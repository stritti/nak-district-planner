## 1. Build and frontend runtime
- [x] 1.1 Add frontend and backend Docker ignore rules
- [x] 1.2 Pin unprivileged frontend Nginx and update all proxy paths to port 8080
- [x] 1.3 Preserve security headers, disable server tokens, and avoid caching app shell/service worker

## 2. Compose and secrets
- [x] 2.1 Add application runtime isolation, limits, service healthchecks
- [x] 2.2 Enforce Valkey auth in development and production Compose and application URL
- [x] 2.3 Validate production runtime credentials and standalone IdP secrets/HTTPS
- [x] 2.4 Preserve literal Valkey passwords in Compose commands and reject URL-unsafe production values

## 3. Restore and documentation
- [x] 3.1 Back up encrypted database and global roles separately
- [x] 3.2 Migrate drill source and verify restored data, grants, RLS and definer functions
- [x] 3.3 Document configuration changes, role restore order and retained CSP decisions

## 4. Verification
- [x] 4.1 Validate Compose interpolation and YAML schemas
- [x] 4.2 Run regression and config tests (coverage >80%)
- [x] 4.3 Run full Docker-based encrypted Restore Drill and review CI checks
- [ ] 4.4 Triage external GitGuardian incident 36714356 for Compose environment-variable interpolation (security gate remains active)

## 5. Production release instructions
- [x] 5.1 Add operator-facing upgrade instructions for Issue #472
- [x] 5.2 Publish newly introduced upgrade instructions ahead of the generated release changelog
- [x] 5.3 Make Docker image release conditional on successful upgrade-note publication
- [x] 5.4 Add behavioral tests for first release, later releases, invalid notes, idempotence, and unchanged changelogs
- [x] 5.5 Document contributor workflow and upgrade-note contract
- [ ] 5.6 Confirm GitHub Actions checks on the updated PR branch
