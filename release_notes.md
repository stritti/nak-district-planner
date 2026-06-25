## [v0.26.1] - 2026-06-25

### Features
* feat(matrix): complete M1 frontend integration with deviation display (#188) (75a13f8)
* feat: tenant isolation (SEC-020, SEC-021) (e197af9)
* feat(matrix): implement PlanningSeries slot generation and deviation display (M1) (#187) (3eb157f)
* feat(security): implement audit logging (SEC-009) (753a502)
* Merge pull request #172 from stritti/feature/security-rate-limiting-sec-016 (dbd4806)
* Merge pull request #186 from stritti/feat/sync-status-card (3a0a7ae)
* Merge pull request #185 from stritti/feat/toast-confirm-dialogs (8a50676)
* Merge pull request #184 from stritti/feat/health-check-endpoint (9a5df96)
* Merge pull request #174 from stritti/feature/matrix-rendering-migration-1-1 (55355e8)
* Merge pull request #169 from stritti/feature/security-csrf-protection-sec-004 (55fb297)

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
* M2 — Notification-System, PlanningSeries Auto-Gen, Matrix-Deviation, Auto-Matching (#189) (e707d5d)
* chore: release v0.26.0 (ded67c9)
* chore: release v0.25.0 (5adc99a)
* chore: release v0.24.0 (1f56d93)
* chore: release v0.23.0 (56bb2ae)
* chore: release v0.22.0 (c6a5d30)
* Merge pull request #148 from stritti/copilot/implement-planningslot-planningseries (837697e)
* Merge remote-tracking branch 'origin/main' into copilot/implement-planningslot-planningseries (fe0bf8f)
* chore: release v0.21.0 (624e522)
* Merge pull request #166 from stritti/vibe/openspec-gap-analysis-71c667 (b081d2c)
