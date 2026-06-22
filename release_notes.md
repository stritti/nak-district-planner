## [v0.23.0] - 2026-06-22

### Features
* feat(security): implement audit logging (SEC-009) (753a502)
* Merge pull request #172 from stritti/feature/security-rate-limiting-sec-016 (dbd4806)
* Merge pull request #186 from stritti/feat/sync-status-card (3a0a7ae)
* Merge pull request #185 from stritti/feat/toast-confirm-dialogs (8a50676)
* Merge pull request #184 from stritti/feat/health-check-endpoint (9a5df96)
* Merge pull request #174 from stritti/feature/matrix-rendering-migration-1-1 (55355e8)
* Merge pull request #169 from stritti/feature/security-csrf-protection-sec-004 (55fb297)
* Merge pull request #154 from stritti/feat/p0-blitzer-production-readiness (8220231)
* feat(security): implement rate limiting (SEC-016) (dce5ec9)
* feat(security): implement CSRF protection (SEC-004) (36a14c8)

### Bug Fixes
* Fix MegaLinter issues: add language specifiers to code blocks, fix trailing spaces, fix table columns, ensure files end with newline (e0a544e)
* fix: remove undefined leader_ids variable from matrix view (7c5e5ca)
* fix: align test files with refactored matrix implementation (c814262)
* fix: correct RBAC gap classification per review feedback (2748d25)
* fix: remove unverified JWT extraction from rate-limit keys; use Docker Redis URL (e79749e)
* fix: restore leader preload for name resolution; fallback event_id for slot-only cells (ce64617)
* fix: update uv.lock, enforce burst limit, fix denial test (9bbb0bf)
* fix: add explanatory comment to CodeQL empty except (013fda3)
* fix: chain migration from current head e4b2a9d7f110; preserve slot-only dates (4d33a6e)
* fix: 4 review issues — CodeQL empty-except, JWT sub extraction, Redis member nonce, count <= limit (33045cc)

### Other Changes
* chore: release v0.22.0 (c6a5d30)
* Merge pull request #148 from stritti/copilot/implement-planningslot-planningseries (837697e)
* Merge remote-tracking branch 'origin/main' into copilot/implement-planningslot-planningseries (fe0bf8f)
* chore: release v0.21.0 (624e522)
* Merge pull request #166 from stritti/vibe/openspec-gap-analysis-71c667 (b081d2c)
* Merge remote-tracking branch 'origin/main' into copilot/implement-planningslot-planningseries (84b257b)
* docs: add OpenSpec gap analysis with prioritized table (1d112d6)
* chore: release v0.20.0 (884b919)
* chore: release v0.19.0 (06ee992)
* chore: release v0.18.0 (eea4ae3)
