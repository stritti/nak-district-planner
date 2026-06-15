## [v0.10.0] - 2026-06-15

### Features
* Merge pull request #152 from stritti/feat/responsive-pwa (e7c4c2c)
* feat: responsive UI + PWA support (d5f0bad)
* Merge pull request #150 from stritti/feat/approval-status (ee43e4e)
* feat: complete approval_status UI and tests (d83782c)
* feat: add approval_status (PLANNED/CONFIRMED) orthogonal to EventStatus (37f13dc)
* feat: proxy OIDC token exchange through backend (76590c3)
* feat: proxy OIDC discovery through backend (no build-time env vars) (03cebe9)
* feat(system): automatic version check and admin-triggered self-update (01bafcb)
* feat(system): implement automatic version check and self-update feature (6c0ce93)
* feat: add specification and design for automatic system version checking and admin-triggered self-updates (e7cd858)

### Bug Fixes
* fix: remove duplicated public/manifest.json, let VitePWA inject manifest (a320106)
* fix: make .page-title responsive, use it in MatrixView (d3191f3)
* fix: remove unused closeMenuOnNavOpen, close menu on hamburger click (74e654c)
* fix: restore w-full text-sm on LeadersAdminView tables (54e9c98)
* fix: restore w-full text-sm on EventListView table (52f6ef9)
* fix: use function matcher for Workbox runtimeCaching urlPattern (cf02323)
* fix: review findings for approval_status PR (b4706fa)
* fix(build): suppress TS 7.0 baseUrl deprecation warning in tsconfig (6efbf45)
* fix(build): add @ alias to tsconfig paths and fix vite alias path for Docker (989fe59)
* fix(db): resolve alembic migration heads conflict and PG18 volume mount (0a6f851)

### Other Changes
* chore: release v0.9.0 (bdee59d)
* chore: release v0.8.0 (57ae834)
* chore: release v0.7.0 (18c3ec4)
* chore: release v0.6.2 (84f061d)
* chore: release v0.6.1 (0ec4662)
* chore: release v0.6.0 (ec47081)
* build: upgrade postgres image version to 18-alpine in docker-compose (22418f4)
* chore: release v0.5.1 (39b80fc)
* refactor: extract hybrid-calendar-sync, external-event-ingestion, in-app-notifications from planning-slot-hybrid-sync (6b1e80c)
* chore: release v0.5.0 (71956f8)
