## [v0.20.1] - 2026-06-20

### Features
* Merge pull request #186 from stritti/feat/sync-status-card (3a0a7ae)
* Merge pull request #185 from stritti/feat/toast-confirm-dialogs (8a50676)
* Merge pull request #184 from stritti/feat/health-check-endpoint (9a5df96)
* Merge pull request #174 from stritti/feature/matrix-rendering-migration-1-1 (55355e8)
* Merge pull request #169 from stritti/feature/security-csrf-protection-sec-004 (55fb297)
* Merge pull request #154 from stritti/feat/p0-blitzer-production-readiness (8220231)
* feat(security): implement CSRF protection (SEC-004) (36a14c8)
* feat: add sync status card component and calendar integrations store (da2bb9f)
* feat: add toast notification system and confirm dialog component (a300ac5)
* feat: add database health check to /api/health endpoint (52df2a9)

### Bug Fixes
* fix: correct RBAC gap classification per review feedback (2748d25)
* Fix duplicate starlette dependency and update requests version (e376147)
* Fix frontend tests: replace @vueuse/integrations with native cookie handling (cc29b50)
* Fix frontend tests: add js-cookie dependency and mock useCSRF in tests (317b9aa)
* Fix MegaLinter markdown issues in CSRF documentation (4a9088b)
* Fix CSRF token parsing bug for session-bound tokens (c445d9c)
* fix: health endpoint always returns ok status, update test (481856f)
* chore: update pydantic-settings to 2.14.2 to fix security vulnerability GHSA-4xgf-cpjx-pc3j (59c326a)
* fix: set event_id to slot.id for frontend compatibility (7a7ffbb)
* fix: add pytest import to feiertage_service tests (a37491e)

### Other Changes
* Merge pull request #166 from stritti/vibe/openspec-gap-analysis-71c667 (b081d2c)
* docs: add OpenSpec gap analysis with prioritized table (1d112d6)
* chore: release v0.20.0 (884b919)
* chore: release v0.19.0 (06ee992)
* chore: release v0.18.0 (eea4ae3)
* chore: release v0.17.0 (769c3e8)
* chore: release v0.16.0 (2c8b5ec)
* chore: release v0.15.0 (5640fc2)
* Merge pull request #181 from stritti/dependabot/uv/services/backend/fastapi-0.138.0 (9678d97)
* Merge pull request #180 from stritti/dependabot/uv/services/backend/pytest-9.1.1 (bc754c6)
