## [v0.28.4] - 2026-07-20

### Features
* Merge pull request #210 from stritti/feat/toast-confirmdialog-consolidation (83d0a64)
* feat(frontend): Toast-Feedback & ConfirmDialog konsolidieren (PR-2) (08bcea4)
* feat(m3): remove legacy Event model — EventInstance + ExternalEventLink + Sync Härtung (#190) (e99a840)
* feat(matrix): complete M1 frontend integration with deviation display (#188) (75a13f8)
* feat: tenant isolation (SEC-020, SEC-021) (e197af9)
* feat(matrix): implement PlanningSeries slot generation and deviation display (M1) (#187) (3eb157f)
* feat(security): implement audit logging (SEC-009) (753a502)
* Merge pull request #172 from stritti/feature/security-rate-limiting-sec-016 (dbd4806)
* Merge pull request #186 from stritti/feat/sync-status-card (3a0a7ae)
* Merge pull request #185 from stritti/feat/toast-confirm-dialogs (8a50676)

### Bug Fixes
* Merge pull request #211 from stritti/fix/csrf-middleware-asgi-crash (9d69581)
* fix(security): CSRFMiddleware crasht bei jedem Request (ASGI-Signatur) (775b63f)
* fix: ConfirmDialog ignoriert loading-Prop im dangerous-Modus nicht mehr (29acd1d)
* Merge pull request #209 from stritti/fix/leaders-link-self-rbac-gap (8824da2)
* fix: congregation-scoped users können self-link weiter nutzen (7116acc)
* fix(security): RBAC-Guard für leaders link-self Endpoints (B-1) (9cb06f1)
* Merge pull request #207 from stritti/fix/pip-audit-cve-joserfc (5e26c41)
* fix: joserfc auf 1.7.3 aktualisiert — CVE-2026-48990, CVE-2026-49852 behoben (a920f40)
* fix: Unit-Tests an require_role_in_district() angepasst (8805894)
* fix: resolve alembic multi-head and FK name length issues (#202) (4619e48)

### Other Changes
* build(deps): Bump alembic from 1.18.4 to 1.18.5 in /services/backend (#230) (02c3c5d)
* chore: release v0.28.3 (92006de)
* build(deps): Bump actions/setup-node from 6 to 7 (#224) (116579e)
* chore: release v0.28.2 (c4da7eb)
* test: coverage oidc 92%, claims_validation 96%, jwt_claims 89% (6fd4a68)
* chore: release v0.28.1 (bf6ef39)
* refactor: RBAC-Guard-Konsolidierung auf require_role_in_district() (PR-4) (5d6c43e)
* chore: release v0.28.0 (2e72c48)
* Merge pull request #212 from stritti/test/coverage-verification-auth-rbac-sync (5e65fbf)
* Merge pull request #222 from stritti/dependabot/uv/services/backend/uvicorn-standard--gte-0.51.0 (e2e006a)
