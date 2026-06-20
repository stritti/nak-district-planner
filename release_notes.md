## [v0.21.0] - 2026-06-20

### Features
* Merge pull request #172 from stritti/feature/security-rate-limiting-sec-016 (dbd4806)
* Merge pull request #186 from stritti/feat/sync-status-card (3a0a7ae)
* Merge pull request #185 from stritti/feat/toast-confirm-dialogs (8a50676)
* Merge pull request #184 from stritti/feat/health-check-endpoint (9a5df96)
* Merge pull request #174 from stritti/feature/matrix-rendering-migration-1-1 (55355e8)
* Merge pull request #169 from stritti/feature/security-csrf-protection-sec-004 (55fb297)
* Merge pull request #154 from stritti/feat/p0-blitzer-production-readiness (8220231)
* feat(security): implement rate limiting (SEC-016) (dce5ec9)
* feat(security): implement CSRF protection (SEC-004) (36a14c8)
* feat: add sync status card component and calendar integrations store (da2bb9f)

### Bug Fixes
* fix: correct RBAC gap classification per review feedback (2748d25)
* fix: remove unverified JWT extraction from rate-limit keys; use Docker Redis URL (e79749e)
* fix: update uv.lock, enforce burst limit, fix denial test (9bbb0bf)
* fix: add explanatory comment to CodeQL empty except (013fda3)
* fix: 4 review issues — CodeQL empty-except, JWT sub extraction, Redis member nonce, count <= limit (33045cc)
* fix: address all review comments on rate-limiting PR (3ebfe61)
* fix: resolve merge conflicts between rate-limit, csrf middleware (d47cfef)
* Fix MegaLinter markdown issues in rate limiting documentation (d16acc2)
* Add missing redis_url config and fix rate limit comparison (1e03f21)
* Fix duplicate starlette dependency and update requests version (e376147)

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
