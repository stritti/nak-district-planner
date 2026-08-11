## [v0.29.3] - 2026-08-11

### Features
* feat(uc-02): persist and display last_sync_error for calendar integrations (b5bcfe3)
* Merge pull request #210 from stritti/feat/toast-confirmdialog-consolidation (83d0a64)
* feat(frontend): Toast-Feedback & ConfirmDialog konsolidieren (PR-2) (08bcea4)
* feat(m3): remove legacy Event model — EventInstance + ExternalEventLink + Sync Härtung (#190) (e99a840)
* feat(matrix): complete M1 frontend integration with deviation display (#188) (75a13f8)
* feat: tenant isolation (SEC-020, SEC-021) (e197af9)
* feat(matrix): implement PlanningSeries slot generation and deviation display (M1) (#187) (3eb157f)
* feat(security): implement audit logging (SEC-009) (753a502)
* Merge pull request #172 from stritti/feature/security-rate-limiting-sec-016 (dbd4806)
* Merge pull request #186 from stritti/feat/sync-status-card (3a0a7ae)

### Bug Fixes
* fix: upgrade click to 8.4.2 to resolve PYSEC-2026-2132 command injection vulnerability (16ef998)
* Merge pull request #211 from stritti/fix/csrf-middleware-asgi-crash (9d69581)
* fix(security): CSRFMiddleware crasht bei jedem Request (ASGI-Signatur) (775b63f)
* fix: ConfirmDialog ignoriert loading-Prop im dangerous-Modus nicht mehr (29acd1d)
* Merge pull request #209 from stritti/fix/leaders-link-self-rbac-gap (8824da2)
* fix: congregation-scoped users können self-link weiter nutzen (7116acc)
* fix(security): RBAC-Guard für leaders link-self Endpoints (B-1) (9cb06f1)
* Merge pull request #207 from stritti/fix/pip-audit-cve-joserfc (5e26c41)
* fix: joserfc auf 1.7.3 aktualisiert — CVE-2026-48990, CVE-2026-49852 behoben (a920f40)
* fix: Unit-Tests an require_role_in_district() angepasst (8805894)

### Other Changes
* chore: release v0.29.2 (4e273b0)
* refactor(uc-01): extract CalendarIntegrationService and raise CalendarConnectorError (#264) (8166064)
* chore: release v0.29.1 (63e30eb)
* docs: mark uc-02 last_sync_error tasks complete (9a8c222)
* chore: release v0.29.0 (4a450bb)
* docs: mark verified-complete tasks in planning-slot, uc-01, rbac changes (fbe37c6)
* ci: optimize actions caching and redundant jobs (#263) (b8efe7c)
* build(deps-dev): Bump vue-tsc to 3.3.9 and typescript-eslint to 8.66.0 in /services/frontend (#262) (b500979)
* build(deps): Bump pinia from 3.0.4 to 4.0.2 in /services/frontend (#254) (de2527d)
* build(deps): Bump redis from 8.0.1 to 8.1.0 in /services/backend (#258) (bac6356)
