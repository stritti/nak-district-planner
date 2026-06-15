## [v0.11.0] - 2026-06-15

### Features
* feat: add pr-review skill for structured review comment handling (ec499a7)
* Merge pull request #152 from stritti/feat/responsive-pwa (e7c4c2c)
* feat: responsive UI + PWA support (d5f0bad)
* Merge pull request #150 from stritti/feat/approval-status (ee43e4e)
* feat: complete approval_status UI and tests (d83782c)
* feat: add approval_status (PLANNED/CONFIRMED) orthogonal to EventStatus (37f13dc)
* feat: proxy OIDC token exchange through backend (76590c3)
* feat: proxy OIDC discovery through backend (no build-time env vars) (03cebe9)
* feat(system): automatic version check and admin-triggered self-update (01bafcb)
* feat(system): implement automatic version check and self-update feature (6c0ce93)

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
* chore: release v0.10.0 (f4cdf03)
* chore: release v0.9.0 (bdee59d)
* chore: release v0.8.0 (57ae834)
* chore: release v0.7.0 (18c3ec4)
* chore: release v0.6.2 (84f061d)
* chore: release v0.6.1 (0ec4662)
* chore: release v0.6.0 (ec47081)
* build: upgrade postgres image version to 18-alpine in docker-compose (22418f4)
* chore: release v0.5.1 (39b80fc)
* refactor: extract hybrid-calendar-sync, external-event-ingestion, in-app-notifications from planning-slot-hybrid-sync (6b1e80c)

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

## [v0.9.0] - 2026-06-12

### Features
* Merge pull request #150 from stritti/feat/approval-status (ee43e4e)
* feat: complete approval_status UI and tests (d83782c)
* feat: add approval_status (PLANNED/CONFIRMED) orthogonal to EventStatus (37f13dc)
* feat: proxy OIDC token exchange through backend (76590c3)
* feat: proxy OIDC discovery through backend (no build-time env vars) (03cebe9)
* feat(system): automatic version check and admin-triggered self-update (01bafcb)
* feat(system): implement automatic version check and self-update feature (6c0ce93)
* feat: add specification and design for automatic system version checking and admin-triggered self-updates (e7cd858)
* feat: add configurable-email-reminders and event-driven-mail-hooks proposals (dfd452b)
* feat: add persistent test database service, enable configurable PostgreSQL ports, migrate Authentik to local bind mounts, and add utility script for database verification. (d226782)

### Bug Fixes
* fix: review findings for approval_status PR (b4706fa)
* fix(build): suppress TS 7.0 baseUrl deprecation warning in tsconfig (6efbf45)
* fix(build): add @ alias to tsconfig paths and fix vite alias path for Docker (989fe59)
* fix(db): resolve alembic migration heads conflict and PG18 volume mount (0a6f851)
* fix(ci): remove trailing spaces and fix markdown lint issues (d06e62b)
* fix(ci): add timezone import and enhance quality-check skills (fe58787)
* fix(ci): fix release workflow issues (1866464)
* fix(ci): complete rewrite of release workflow with conventional commits (1f8cd3b)
* fix(ci): switch to tag-based releases (b18d75c)
* fix(ci): add skip-release-pulls parameter directly to workflow (330e9e7)

### Other Changes
* chore: release v0.8.0 (57ae834)
* chore: release v0.7.0 (18c3ec4)
* chore: release v0.6.2 (84f061d)
* chore: release v0.6.1 (0ec4662)
* chore: release v0.6.0 (ec47081)
* build: upgrade postgres image version to 18-alpine in docker-compose (22418f4)
* chore: release v0.5.1 (39b80fc)
* refactor: extract hybrid-calendar-sync, external-event-ingestion, in-app-notifications from planning-slot-hybrid-sync (6b1e80c)
* chore: release v0.5.0 (71956f8)
* Merge branch 'main' of github.com:stritti/nak-district-planner (2d7de1e)

## [v0.8.0] - 2026-06-10

### Features
* feat: proxy OIDC token exchange through backend (76590c3)
* feat: proxy OIDC discovery through backend (no build-time env vars) (03cebe9)
* feat(system): automatic version check and admin-triggered self-update (01bafcb)
* feat(system): implement automatic version check and self-update feature (6c0ce93)
* feat: add specification and design for automatic system version checking and admin-triggered self-updates (e7cd858)
* feat: add configurable-email-reminders and event-driven-mail-hooks proposals (dfd452b)
* feat: add persistent test database service, enable configurable PostgreSQL ports, migrate Authentik to local bind mounts, and add utility script for database verification. (d226782)
* feat(matrix): close remaining UC-03 implementation gaps (#93) (9ab555a)
* feat(matrix): complete remaining UC-03 matrix tasks (#90) (bc98e71)
* feat: add checks skill for code quality verification (eadd177)

### Bug Fixes
* fix(build): suppress TS 7.0 baseUrl deprecation warning in tsconfig (6efbf45)
* fix(build): add @ alias to tsconfig paths and fix vite alias path for Docker (989fe59)
* fix(db): resolve alembic migration heads conflict and PG18 volume mount (0a6f851)
* fix(ci): remove trailing spaces and fix markdown lint issues (d06e62b)
* fix(ci): add timezone import and enhance quality-check skills (fe58787)
* fix(ci): fix release workflow issues (1866464)
* fix(ci): complete rewrite of release workflow with conventional commits (1f8cd3b)
* fix(ci): switch to tag-based releases (b18d75c)
* fix(ci): add skip-release-pulls parameter directly to workflow (330e9e7)
* fix(ci): enable automatic releases on push to main (e07d439)

### Other Changes
* chore: release v0.7.0 (18c3ec4)
* chore: release v0.6.2 (84f061d)
* chore: release v0.6.1 (0ec4662)
* chore: release v0.6.0 (ec47081)
* build: upgrade postgres image version to 18-alpine in docker-compose (22418f4)
* chore: release v0.5.1 (39b80fc)
* refactor: extract hybrid-calendar-sync, external-event-ingestion, in-app-notifications from planning-slot-hybrid-sync (6b1e80c)
* chore: release v0.5.0 (71956f8)
* Merge branch 'main' of github.com:stritti/nak-district-planner (2d7de1e)
* build(deps-dev): Bump ruff from 0.15.13 to 0.15.14 in /services/backend (#132) (fa72eef)

## [v0.7.0] - 2026-06-10

### Features
* feat: proxy OIDC discovery through backend (no build-time env vars) (03cebe9)
* feat(system): automatic version check and admin-triggered self-update (01bafcb)
* feat(system): implement automatic version check and self-update feature (6c0ce93)
* feat: add specification and design for automatic system version checking and admin-triggered self-updates (e7cd858)
* feat: add configurable-email-reminders and event-driven-mail-hooks proposals (dfd452b)
* feat: add persistent test database service, enable configurable PostgreSQL ports, migrate Authentik to local bind mounts, and add utility script for database verification. (d226782)
* feat(matrix): close remaining UC-03 implementation gaps (#93) (9ab555a)
* feat(matrix): complete remaining UC-03 matrix tasks (#90) (bc98e71)
* feat: add checks skill for code quality verification (eadd177)
* feat: add pluggable IDP provisioning layer (63d5e66)

### Bug Fixes
* fix(build): suppress TS 7.0 baseUrl deprecation warning in tsconfig (6efbf45)
* fix(build): add @ alias to tsconfig paths and fix vite alias path for Docker (989fe59)
* fix(db): resolve alembic migration heads conflict and PG18 volume mount (0a6f851)
* fix(ci): remove trailing spaces and fix markdown lint issues (d06e62b)
* fix(ci): add timezone import and enhance quality-check skills (fe58787)
* fix(ci): fix release workflow issues (1866464)
* fix(ci): complete rewrite of release workflow with conventional commits (1f8cd3b)
* fix(ci): switch to tag-based releases (b18d75c)
* fix(ci): add skip-release-pulls parameter directly to workflow (330e9e7)
* fix(ci): enable automatic releases on push to main (e07d439)

### Other Changes
* chore: release v0.6.2 (84f061d)
* chore: release v0.6.1 (0ec4662)
* chore: release v0.6.0 (ec47081)
* build: upgrade postgres image version to 18-alpine in docker-compose (22418f4)
* chore: release v0.5.1 (39b80fc)
* refactor: extract hybrid-calendar-sync, external-event-ingestion, in-app-notifications from planning-slot-hybrid-sync (6b1e80c)
* chore: release v0.5.0 (71956f8)
* Merge branch 'main' of github.com:stritti/nak-district-planner (2d7de1e)
* build(deps-dev): Bump ruff from 0.15.13 to 0.15.14 in /services/backend (#132) (fa72eef)
* build(deps-dev): Bump vite from 8.0.13 to 8.0.16 in /services/frontend (#133) (c4c447e)

## [v0.6.2] - 2026-06-10

### Features
* feat(system): automatic version check and admin-triggered self-update (01bafcb)
* feat(system): implement automatic version check and self-update feature (6c0ce93)
* feat: add specification and design for automatic system version checking and admin-triggered self-updates (e7cd858)
* feat: add configurable-email-reminders and event-driven-mail-hooks proposals (dfd452b)
* feat: add persistent test database service, enable configurable PostgreSQL ports, migrate Authentik to local bind mounts, and add utility script for database verification. (d226782)
* feat(matrix): close remaining UC-03 implementation gaps (#93) (9ab555a)
* feat(matrix): complete remaining UC-03 matrix tasks (#90) (bc98e71)
* feat: add checks skill for code quality verification (eadd177)
* feat: add pluggable IDP provisioning layer (63d5e66)
* feat: add approval-based IDP onboarding and pending alerts (06b84c3)

### Bug Fixes
* fix(build): suppress TS 7.0 baseUrl deprecation warning in tsconfig (6efbf45)
* fix(build): add @ alias to tsconfig paths and fix vite alias path for Docker (989fe59)
* fix(db): resolve alembic migration heads conflict and PG18 volume mount (0a6f851)
* fix(ci): remove trailing spaces and fix markdown lint issues (d06e62b)
* fix(ci): add timezone import and enhance quality-check skills (fe58787)
* fix(ci): fix release workflow issues (1866464)
* fix(ci): complete rewrite of release workflow with conventional commits (1f8cd3b)
* fix(ci): switch to tag-based releases (b18d75c)
* fix(ci): add skip-release-pulls parameter directly to workflow (330e9e7)
* fix(ci): enable automatic releases on push to main (e07d439)

### Other Changes
* chore: release v0.6.1 (0ec4662)
* chore: release v0.6.0 (ec47081)
* build: upgrade postgres image version to 18-alpine in docker-compose (22418f4)
* chore: release v0.5.1 (39b80fc)
* refactor: extract hybrid-calendar-sync, external-event-ingestion, in-app-notifications from planning-slot-hybrid-sync (6b1e80c)
* chore: release v0.5.0 (71956f8)
* Merge branch 'main' of github.com:stritti/nak-district-planner (2d7de1e)
* build(deps-dev): Bump ruff from 0.15.13 to 0.15.14 in /services/backend (#132) (fa72eef)
* build(deps-dev): Bump vite from 8.0.13 to 8.0.16 in /services/frontend (#133) (c4c447e)
* build(deps-dev): Bump @vitejs/plugin-vue in /services/frontend (#130) (b08a08f)

## [v0.6.1] - 2026-06-10

### Features
* feat(system): automatic version check and admin-triggered self-update (01bafcb)
* feat(system): implement automatic version check and self-update feature (6c0ce93)
* feat: add specification and design for automatic system version checking and admin-triggered self-updates (e7cd858)
* feat: add configurable-email-reminders and event-driven-mail-hooks proposals (dfd452b)
* feat: add persistent test database service, enable configurable PostgreSQL ports, migrate Authentik to local bind mounts, and add utility script for database verification. (d226782)
* feat(matrix): close remaining UC-03 implementation gaps (#93) (9ab555a)
* feat(matrix): complete remaining UC-03 matrix tasks (#90) (bc98e71)
* feat: add checks skill for code quality verification (eadd177)
* feat: add pluggable IDP provisioning layer (63d5e66)
* feat: add approval-based IDP onboarding and pending alerts (06b84c3)

### Bug Fixes
* fix(build): add @ alias to tsconfig paths and fix vite alias path for Docker (989fe59)
* fix(db): resolve alembic migration heads conflict and PG18 volume mount (0a6f851)
* fix(ci): remove trailing spaces and fix markdown lint issues (d06e62b)
* fix(ci): add timezone import and enhance quality-check skills (fe58787)
* fix(ci): fix release workflow issues (1866464)
* fix(ci): complete rewrite of release workflow with conventional commits (1f8cd3b)
* fix(ci): switch to tag-based releases (b18d75c)
* fix(ci): add skip-release-pulls parameter directly to workflow (330e9e7)
* fix(ci): enable automatic releases on push to main (e07d439)
* fix(ci): change release workflow trigger from push to workflow_dispatch (d24686b)

### Other Changes
* chore: release v0.6.0 (ec47081)
* build: upgrade postgres image version to 18-alpine in docker-compose (22418f4)
* chore: release v0.5.1 (39b80fc)
* refactor: extract hybrid-calendar-sync, external-event-ingestion, in-app-notifications from planning-slot-hybrid-sync (6b1e80c)
* chore: release v0.5.0 (71956f8)
* Merge branch 'main' of github.com:stritti/nak-district-planner (2d7de1e)
* build(deps-dev): Bump ruff from 0.15.13 to 0.15.14 in /services/backend (#132) (fa72eef)
* build(deps-dev): Bump vite from 8.0.13 to 8.0.16 in /services/frontend (#133) (c4c447e)
* build(deps-dev): Bump @vitejs/plugin-vue in /services/frontend (#130) (b08a08f)
* Remediate pip-audit failure by constraining Starlette to a non-vulnerable version (#137) (a1fcb0d)

## [v0.6.0] - 2026-06-10

### Features
* feat(system): automatic version check and admin-triggered self-update (01bafcb)
* feat(system): implement automatic version check and self-update feature (6c0ce93)
* feat: add specification and design for automatic system version checking and admin-triggered self-updates (e7cd858)
* feat: add configurable-email-reminders and event-driven-mail-hooks proposals (dfd452b)
* feat: add persistent test database service, enable configurable PostgreSQL ports, migrate Authentik to local bind mounts, and add utility script for database verification. (d226782)
* feat(matrix): close remaining UC-03 implementation gaps (#93) (9ab555a)
* feat(matrix): complete remaining UC-03 matrix tasks (#90) (bc98e71)
* feat: add checks skill for code quality verification (eadd177)
* feat: add pluggable IDP provisioning layer (63d5e66)
* feat: add approval-based IDP onboarding and pending alerts (06b84c3)

### Bug Fixes
* fix(db): resolve alembic migration heads conflict and PG18 volume mount (0a6f851)
* fix(ci): remove trailing spaces and fix markdown lint issues (d06e62b)
* fix(ci): add timezone import and enhance quality-check skills (fe58787)
* fix(ci): fix release workflow issues (1866464)
* fix(ci): complete rewrite of release workflow with conventional commits (1f8cd3b)
* fix(ci): switch to tag-based releases (b18d75c)
* fix(ci): add skip-release-pulls parameter directly to workflow (330e9e7)
* fix(ci): enable automatic releases on push to main (e07d439)
* fix(ci): change release workflow trigger from push to workflow_dispatch (d24686b)
* fix: remove ignore (074ebdb)

### Other Changes
* build: upgrade postgres image version to 18-alpine in docker-compose (22418f4)
* chore: release v0.5.1 (39b80fc)
* refactor: extract hybrid-calendar-sync, external-event-ingestion, in-app-notifications from planning-slot-hybrid-sync (6b1e80c)
* chore: release v0.5.0 (71956f8)
* Merge branch 'main' of github.com:stritti/nak-district-planner (2d7de1e)
* build(deps-dev): Bump ruff from 0.15.13 to 0.15.14 in /services/backend (#132) (fa72eef)
* build(deps-dev): Bump vite from 8.0.13 to 8.0.16 in /services/frontend (#133) (c4c447e)
* build(deps-dev): Bump @vitejs/plugin-vue in /services/frontend (#130) (b08a08f)
* Remediate pip-audit failure by constraining Starlette to a non-vulnerable version (#137) (a1fcb0d)
* build(deps): Bump psycopg2-binary in /services/backend (#134) (4134d4c)

## [v0.5.1] - 2026-06-10

### Features
* feat: add specification and design for automatic system version checking and admin-triggered self-updates (e7cd858)
* feat: add configurable-email-reminders and event-driven-mail-hooks proposals (dfd452b)
* feat: add persistent test database service, enable configurable PostgreSQL ports, migrate Authentik to local bind mounts, and add utility script for database verification. (d226782)
* feat(matrix): close remaining UC-03 implementation gaps (#93) (9ab555a)
* feat(matrix): complete remaining UC-03 matrix tasks (#90) (bc98e71)
* feat: add checks skill for code quality verification (eadd177)
* feat: add pluggable IDP provisioning layer (63d5e66)
* feat: add approval-based IDP onboarding and pending alerts (06b84c3)
* feat: add openspec configuration for auto-generating 8-week draft services (a0565a6)
* feat: add OpenSpec for approved IDP onboarding (ffe095a)

### Bug Fixes
* fix(ci): remove trailing spaces and fix markdown lint issues (d06e62b)
* fix(ci): add timezone import and enhance quality-check skills (fe58787)
* fix(ci): fix release workflow issues (1866464)
* fix(ci): complete rewrite of release workflow with conventional commits (1f8cd3b)
* fix(ci): switch to tag-based releases (b18d75c)
* fix(ci): add skip-release-pulls parameter directly to workflow (330e9e7)
* fix(ci): enable automatic releases on push to main (e07d439)
* fix(ci): change release workflow trigger from push to workflow_dispatch (d24686b)
* fix: remove ignore (074ebdb)
* fix: synchronize active district selection across admin views (8a46758)

### Other Changes
* refactor: extract hybrid-calendar-sync, external-event-ingestion, in-app-notifications from planning-slot-hybrid-sync (6b1e80c)
* chore: release v0.5.0 (71956f8)
* Merge branch 'main' of github.com:stritti/nak-district-planner (2d7de1e)
* build(deps-dev): Bump ruff from 0.15.13 to 0.15.14 in /services/backend (#132) (fa72eef)
* build(deps-dev): Bump vite from 8.0.13 to 8.0.16 in /services/frontend (#133) (c4c447e)
* build(deps-dev): Bump @vitejs/plugin-vue in /services/frontend (#130) (b08a08f)
* Remediate pip-audit failure by constraining Starlette to a non-vulnerable version (#137) (a1fcb0d)
* build(deps): Bump psycopg2-binary in /services/backend (#134) (4134d4c)
* build(deps-dev): Bump vue-tsc from 3.2.6 to 3.3.1 in /services/frontend (#131) (3b07398)
* build(deps): Bump @vueuse/core in /services/frontend (#129) (1fdf9c9)

## [v0.5.0] - 2026-06-10

### Features
* feat: add specification and design for automatic system version checking and admin-triggered self-updates (e7cd858)
* feat: add configurable-email-reminders and event-driven-mail-hooks proposals (dfd452b)
* feat: add persistent test database service, enable configurable PostgreSQL ports, migrate Authentik to local bind mounts, and add utility script for database verification. (d226782)
* feat(matrix): close remaining UC-03 implementation gaps (#93) (9ab555a)
* feat(matrix): complete remaining UC-03 matrix tasks (#90) (bc98e71)
* feat: add checks skill for code quality verification (eadd177)
* feat: add pluggable IDP provisioning layer (63d5e66)
* feat: add approval-based IDP onboarding and pending alerts (06b84c3)
* feat: add openspec configuration for auto-generating 8-week draft services (a0565a6)
* feat: add OpenSpec for approved IDP onboarding (ffe095a)

### Bug Fixes
* fix(ci): remove trailing spaces and fix markdown lint issues (d06e62b)
* fix(ci): add timezone import and enhance quality-check skills (fe58787)
* fix(ci): fix release workflow issues (1866464)
* fix(ci): complete rewrite of release workflow with conventional commits (1f8cd3b)
* fix(ci): switch to tag-based releases (b18d75c)
* fix(ci): add skip-release-pulls parameter directly to workflow (330e9e7)
* fix(ci): enable automatic releases on push to main (e07d439)
* fix(ci): change release workflow trigger from push to workflow_dispatch (d24686b)
* fix: remove ignore (074ebdb)
* fix: synchronize active district selection across admin views (8a46758)

### Other Changes
* Merge branch 'main' of github.com:stritti/nak-district-planner (2d7de1e)
* build(deps-dev): Bump ruff from 0.15.13 to 0.15.14 in /services/backend (#132) (fa72eef)
* build(deps-dev): Bump vite from 8.0.13 to 8.0.16 in /services/frontend (#133) (c4c447e)
* build(deps-dev): Bump @vitejs/plugin-vue in /services/frontend (#130) (b08a08f)
* Remediate pip-audit failure by constraining Starlette to a non-vulnerable version (#137) (a1fcb0d)
* build(deps): Bump psycopg2-binary in /services/backend (#134) (4134d4c)
* build(deps-dev): Bump vue-tsc from 3.2.6 to 3.3.1 in /services/frontend (#131) (3b07398)
* build(deps): Bump @vueuse/core in /services/frontend (#129) (1fdf9c9)
* build(deps): Bump opentelemetry-instrumentation-celery (#128) (a2fc490)
* build(deps-dev): Bump typescript-eslint in /services/frontend (#127) (0a31d36)

## [v0.4.5] - 2026-04-26

### Features
* feat(matrix): close remaining UC-03 implementation gaps (#93) (9ab555a)
* feat(matrix): complete remaining UC-03 matrix tasks (#90) (bc98e71)
* feat: add checks skill for code quality verification (eadd177)
* feat: add pluggable IDP provisioning layer (63d5e66)
* feat: add approval-based IDP onboarding and pending alerts (06b84c3)
* feat: add openspec configuration for auto-generating 8-week draft services (a0565a6)
* feat: add OpenSpec for approved IDP onboarding (ffe095a)
* feat: group congregations and sync district selection (ef51686)
* feat: optimize matrix view for wider, denser planning (0c0ca94)
* feat: add draft generation and matrix move workflow (e45f958)

### Bug Fixes
* fix(ci): remove trailing spaces and fix markdown lint issues (d06e62b)
* fix(ci): add timezone import and enhance quality-check skills (fe58787)
* fix(ci): fix release workflow issues (1866464)
* fix(ci): complete rewrite of release workflow with conventional commits (1f8cd3b)
* fix(ci): switch to tag-based releases (b18d75c)
* fix(ci): add skip-release-pulls parameter directly to workflow (330e9e7)
* fix(ci): enable automatic releases on push to main (e07d439)
* fix(ci): change release workflow trigger from push to workflow_dispatch (d24686b)
* fix: remove ignore (074ebdb)
* fix: synchronize active district selection across admin views (8a46758)

### Other Changes
* build(deps): Update pydantic[email] requirement in /services/backend (#104) (dfaf12b)
* build(deps-dev): Bump @vue/test-utils in /services/frontend (#102) (8219c37)
* chore: release v0.4.4 (2607b08)
* build(deps-dev): Bump vitest from 4.1.4 to 4.1.5 in /services/frontend (#97) (7c35f65)
* chore: release v0.4.3 (a2041ec)
* build(deps): Bump opentelemetry-instrumentation-fastapi (#96) (5825a53)
* chore: release v0.4.2 (c5e795f)
* build(deps-dev): Bump tailwindcss in /services/frontend (#95) (5cf0986)
* chore: release v0.4.1 (77f6528)
* build(deps-dev): Bump typescript from 5.9.3 to 6.0.3 in /services/frontend (#87) (2521ec8)

## [v0.4.4] - 2026-04-26

### Features
* feat(matrix): close remaining UC-03 implementation gaps (#93) (9ab555a)
* feat(matrix): complete remaining UC-03 matrix tasks (#90) (bc98e71)
* feat: add checks skill for code quality verification (eadd177)
* feat: add pluggable IDP provisioning layer (63d5e66)
* feat: add approval-based IDP onboarding and pending alerts (06b84c3)
* feat: add openspec configuration for auto-generating 8-week draft services (a0565a6)
* feat: add OpenSpec for approved IDP onboarding (ffe095a)
* feat: group congregations and sync district selection (ef51686)
* feat: optimize matrix view for wider, denser planning (0c0ca94)
* feat: add draft generation and matrix move workflow (e45f958)

### Bug Fixes
* fix(ci): remove trailing spaces and fix markdown lint issues (d06e62b)
* fix(ci): add timezone import and enhance quality-check skills (fe58787)
* fix(ci): fix release workflow issues (1866464)
* fix(ci): complete rewrite of release workflow with conventional commits (1f8cd3b)
* fix(ci): switch to tag-based releases (b18d75c)
* fix(ci): add skip-release-pulls parameter directly to workflow (330e9e7)
* fix(ci): enable automatic releases on push to main (e07d439)
* fix(ci): change release workflow trigger from push to workflow_dispatch (d24686b)
* fix: remove ignore (074ebdb)
* fix: synchronize active district selection across admin views (8a46758)

### Other Changes
* build(deps-dev): Bump vitest from 4.1.4 to 4.1.5 in /services/frontend (#97) (7c35f65)
* chore: release v0.4.3 (a2041ec)
* build(deps): Bump opentelemetry-instrumentation-fastapi (#96) (5825a53)
* chore: release v0.4.2 (c5e795f)
* build(deps-dev): Bump tailwindcss in /services/frontend (#95) (5cf0986)
* chore: release v0.4.1 (77f6528)
* build(deps-dev): Bump typescript from 5.9.3 to 6.0.3 in /services/frontend (#87) (2521ec8)
* chore: release v0.4.0 (530248b)
* chore: release v0.3.1 (da47819)
* Harden RBAC on read APIs and scoped district checks (#92) (64b1e17)

## [v0.4.3] - 2026-04-26

### Features
* feat(matrix): close remaining UC-03 implementation gaps (#93) (9ab555a)
* feat(matrix): complete remaining UC-03 matrix tasks (#90) (bc98e71)
* feat: add checks skill for code quality verification (eadd177)
* feat: add pluggable IDP provisioning layer (63d5e66)
* feat: add approval-based IDP onboarding and pending alerts (06b84c3)
* feat: add openspec configuration for auto-generating 8-week draft services (a0565a6)
* feat: add OpenSpec for approved IDP onboarding (ffe095a)
* feat: group congregations and sync district selection (ef51686)
* feat: optimize matrix view for wider, denser planning (0c0ca94)
* feat: add draft generation and matrix move workflow (e45f958)

### Bug Fixes
* fix(ci): remove trailing spaces and fix markdown lint issues (d06e62b)
* fix(ci): add timezone import and enhance quality-check skills (fe58787)
* fix(ci): fix release workflow issues (1866464)
* fix(ci): complete rewrite of release workflow with conventional commits (1f8cd3b)
* fix(ci): switch to tag-based releases (b18d75c)
* fix(ci): add skip-release-pulls parameter directly to workflow (330e9e7)
* fix(ci): enable automatic releases on push to main (e07d439)
* fix(ci): change release workflow trigger from push to workflow_dispatch (d24686b)
* fix: remove ignore (074ebdb)
* fix: synchronize active district selection across admin views (8a46758)

### Other Changes
* build(deps): Bump opentelemetry-instrumentation-fastapi (#96) (5825a53)
* chore: release v0.4.2 (c5e795f)
* build(deps-dev): Bump tailwindcss in /services/frontend (#95) (5cf0986)
* chore: release v0.4.1 (77f6528)
* build(deps-dev): Bump typescript from 5.9.3 to 6.0.3 in /services/frontend (#87) (2521ec8)
* chore: release v0.4.0 (530248b)
* chore: release v0.3.1 (da47819)
* Harden RBAC on read APIs and scoped district checks (#92) (64b1e17)
* chore: release v0.3.0 (c2a0f7d)
* chore: release v0.2.10 (8b338c0)

## [v0.4.2] - 2026-04-26

### Features
* feat(matrix): close remaining UC-03 implementation gaps (#93) (9ab555a)
* feat(matrix): complete remaining UC-03 matrix tasks (#90) (bc98e71)
* feat: add checks skill for code quality verification (eadd177)
* feat: add pluggable IDP provisioning layer (63d5e66)
* feat: add approval-based IDP onboarding and pending alerts (06b84c3)
* feat: add openspec configuration for auto-generating 8-week draft services (a0565a6)
* feat: add OpenSpec for approved IDP onboarding (ffe095a)
* feat: group congregations and sync district selection (ef51686)
* feat: optimize matrix view for wider, denser planning (0c0ca94)
* feat: add draft generation and matrix move workflow (e45f958)

### Bug Fixes
* fix(ci): remove trailing spaces and fix markdown lint issues (d06e62b)
* fix(ci): add timezone import and enhance quality-check skills (fe58787)
* fix(ci): fix release workflow issues (1866464)
* fix(ci): complete rewrite of release workflow with conventional commits (1f8cd3b)
* fix(ci): switch to tag-based releases (b18d75c)
* fix(ci): add skip-release-pulls parameter directly to workflow (330e9e7)
* fix(ci): enable automatic releases on push to main (e07d439)
* fix(ci): change release workflow trigger from push to workflow_dispatch (d24686b)
* fix: remove ignore (074ebdb)
* fix: synchronize active district selection across admin views (8a46758)

### Other Changes
* build(deps-dev): Bump tailwindcss in /services/frontend (#95) (5cf0986)
* chore: release v0.4.1 (77f6528)
* build(deps-dev): Bump typescript from 5.9.3 to 6.0.3 in /services/frontend (#87) (2521ec8)
* chore: release v0.4.0 (530248b)
* chore: release v0.3.1 (da47819)
* Harden RBAC on read APIs and scoped district checks (#92) (64b1e17)
* chore: release v0.3.0 (c2a0f7d)
* chore: release v0.2.10 (8b338c0)
* build(deps-dev): Bump eslint from 10.0.3 to 10.2.1 in /services/frontend (#88) (f0a5bc5)
* chore: release v0.2.9 (698f1b3)

## [v0.4.1] - 2026-04-24

### Features
* feat(matrix): close remaining UC-03 implementation gaps (#93) (9ab555a)
* feat(matrix): complete remaining UC-03 matrix tasks (#90) (bc98e71)
* feat: add checks skill for code quality verification (eadd177)
* feat: add pluggable IDP provisioning layer (63d5e66)
* feat: add approval-based IDP onboarding and pending alerts (06b84c3)
* feat: add openspec configuration for auto-generating 8-week draft services (a0565a6)
* feat: add OpenSpec for approved IDP onboarding (ffe095a)
* feat: group congregations and sync district selection (ef51686)
* feat: optimize matrix view for wider, denser planning (0c0ca94)
* feat: add draft generation and matrix move workflow (e45f958)

### Bug Fixes
* fix(ci): remove trailing spaces and fix markdown lint issues (d06e62b)
* fix(ci): add timezone import and enhance quality-check skills (fe58787)
* fix(ci): fix release workflow issues (1866464)
* fix(ci): complete rewrite of release workflow with conventional commits (1f8cd3b)
* fix(ci): switch to tag-based releases (b18d75c)
* fix(ci): add skip-release-pulls parameter directly to workflow (330e9e7)
* fix(ci): enable automatic releases on push to main (e07d439)
* fix(ci): change release workflow trigger from push to workflow_dispatch (d24686b)
* fix: remove ignore (074ebdb)
* fix: synchronize active district selection across admin views (8a46758)

### Other Changes
* build(deps-dev): Bump typescript from 5.9.3 to 6.0.3 in /services/frontend (#87) (2521ec8)
* chore: release v0.4.0 (530248b)
* chore: release v0.3.1 (da47819)
* Harden RBAC on read APIs and scoped district checks (#92) (64b1e17)
* chore: release v0.3.0 (c2a0f7d)
* chore: release v0.2.10 (8b338c0)
* build(deps-dev): Bump eslint from 10.0.3 to 10.2.1 in /services/frontend (#88) (f0a5bc5)
* chore: release v0.2.9 (698f1b3)
* build(deps): Update pydantic[email] requirement in /services/backend (#89) (572b7ef)
* chore: release v0.2.8 (ea072cf)

## [v0.4.0] - 2026-04-23

### Features
* feat(matrix): close remaining UC-03 implementation gaps (#93) (9ab555a)
* feat(matrix): complete remaining UC-03 matrix tasks (#90) (bc98e71)
* feat: add checks skill for code quality verification (eadd177)
* feat: add pluggable IDP provisioning layer (63d5e66)
* feat: add approval-based IDP onboarding and pending alerts (06b84c3)
* feat: add openspec configuration for auto-generating 8-week draft services (a0565a6)
* feat: add OpenSpec for approved IDP onboarding (ffe095a)
* feat: group congregations and sync district selection (ef51686)
* feat: optimize matrix view for wider, denser planning (0c0ca94)
* feat: add draft generation and matrix move workflow (e45f958)

### Bug Fixes
* fix(ci): remove trailing spaces and fix markdown lint issues (d06e62b)
* fix(ci): add timezone import and enhance quality-check skills (fe58787)
* fix(ci): fix release workflow issues (1866464)
* fix(ci): complete rewrite of release workflow with conventional commits (1f8cd3b)
* fix(ci): switch to tag-based releases (b18d75c)
* fix(ci): add skip-release-pulls parameter directly to workflow (330e9e7)
* fix(ci): enable automatic releases on push to main (e07d439)
* fix(ci): change release workflow trigger from push to workflow_dispatch (d24686b)
* fix: remove ignore (074ebdb)
* fix: synchronize active district selection across admin views (8a46758)

### Other Changes
* chore: release v0.3.1 (da47819)
* Harden RBAC on read APIs and scoped district checks (#92) (64b1e17)
* chore: release v0.3.0 (c2a0f7d)
* chore: release v0.2.10 (8b338c0)
* build(deps-dev): Bump eslint from 10.0.3 to 10.2.1 in /services/frontend (#88) (f0a5bc5)
* chore: release v0.2.9 (698f1b3)
* build(deps): Update pydantic[email] requirement in /services/backend (#89) (572b7ef)
* chore: release v0.2.8 (ea072cf)
* build(deps): Bump authlib (#91) (8a9119f)
* chore: release v0.2.7 (fd60fe3)

## [v0.3.1] - 2026-04-20

### Features
* feat(matrix): complete remaining UC-03 matrix tasks (#90) (bc98e71)
* feat: add checks skill for code quality verification (eadd177)
* feat: add pluggable IDP provisioning layer (63d5e66)
* feat: add approval-based IDP onboarding and pending alerts (06b84c3)
* feat: add openspec configuration for auto-generating 8-week draft services (a0565a6)
* feat: add OpenSpec for approved IDP onboarding (ffe095a)
* feat: group congregations and sync district selection (ef51686)
* feat: optimize matrix view for wider, denser planning (0c0ca94)
* feat: add draft generation and matrix move workflow (e45f958)
* feat: add event-based invitation workflow in service matrix (6875958)

### Bug Fixes
* fix(ci): remove trailing spaces and fix markdown lint issues (d06e62b)
* fix(ci): add timezone import and enhance quality-check skills (fe58787)
* fix(ci): fix release workflow issues (1866464)
* fix(ci): complete rewrite of release workflow with conventional commits (1f8cd3b)
* fix(ci): switch to tag-based releases (b18d75c)
* fix(ci): add skip-release-pulls parameter directly to workflow (330e9e7)
* fix(ci): enable automatic releases on push to main (e07d439)
* fix(ci): change release workflow trigger from push to workflow_dispatch (d24686b)
* fix: remove ignore (074ebdb)
* fix: synchronize active district selection across admin views (8a46758)

### Other Changes
* Harden RBAC on read APIs and scoped district checks (#92) (64b1e17)
* chore: release v0.3.0 (c2a0f7d)
* chore: release v0.2.10 (8b338c0)
* build(deps-dev): Bump eslint from 10.0.3 to 10.2.1 in /services/frontend (#88) (f0a5bc5)
* chore: release v0.2.9 (698f1b3)
* build(deps): Update pydantic[email] requirement in /services/backend (#89) (572b7ef)
* chore: release v0.2.8 (ea072cf)
* build(deps): Bump authlib (#91) (8a9119f)
* chore: release v0.2.7 (fd60fe3)
* build(deps): Update celery[sqlalchemy] requirement in /services/backend (#86) (3c8fed3)

## [v0.3.0] - 2026-04-20

### Features
* feat(matrix): complete remaining UC-03 matrix tasks (#90) (bc98e71)
* feat: add checks skill for code quality verification (eadd177)
* feat: add pluggable IDP provisioning layer (63d5e66)
* feat: add approval-based IDP onboarding and pending alerts (06b84c3)
* feat: add openspec configuration for auto-generating 8-week draft services (a0565a6)
* feat: add OpenSpec for approved IDP onboarding (ffe095a)
* feat: group congregations and sync district selection (ef51686)
* feat: optimize matrix view for wider, denser planning (0c0ca94)
* feat: add draft generation and matrix move workflow (e45f958)
* feat: add event-based invitation workflow in service matrix (6875958)

### Bug Fixes
* fix(ci): remove trailing spaces and fix markdown lint issues (d06e62b)
* fix(ci): add timezone import and enhance quality-check skills (fe58787)
* fix(ci): fix release workflow issues (1866464)
* fix(ci): complete rewrite of release workflow with conventional commits (1f8cd3b)
* fix(ci): switch to tag-based releases (b18d75c)
* fix(ci): add skip-release-pulls parameter directly to workflow (330e9e7)
* fix(ci): enable automatic releases on push to main (e07d439)
* fix(ci): change release workflow trigger from push to workflow_dispatch (d24686b)
* fix: remove ignore (074ebdb)
* fix: synchronize active district selection across admin views (8a46758)

### Other Changes
* chore: release v0.2.10 (8b338c0)
* build(deps-dev): Bump eslint from 10.0.3 to 10.2.1 in /services/frontend (#88) (f0a5bc5)
* chore: release v0.2.9 (698f1b3)
* build(deps): Update pydantic[email] requirement in /services/backend (#89) (572b7ef)
* chore: release v0.2.8 (ea072cf)
* build(deps): Bump authlib (#91) (8a9119f)
* chore: release v0.2.7 (fd60fe3)
* build(deps): Update celery[sqlalchemy] requirement in /services/backend (#86) (3c8fed3)
* chore: release v0.2.6 (fbfa5af)
* build(deps): Bump actions/checkout from 4 to 6 (#85) (0bd1ef6)

## [v0.2.10] - 2026-04-19

### Features
* feat: add checks skill for code quality verification (eadd177)
* feat: add pluggable IDP provisioning layer (63d5e66)
* feat: add approval-based IDP onboarding and pending alerts (06b84c3)
* feat: add openspec configuration for auto-generating 8-week draft services (a0565a6)
* feat: add OpenSpec for approved IDP onboarding (ffe095a)
* feat: group congregations and sync district selection (ef51686)
* feat: optimize matrix view for wider, denser planning (0c0ca94)
* feat: add draft generation and matrix move workflow (e45f958)
* feat: add event-based invitation workflow in service matrix (6875958)
* feat: add state variables for self-linking leaders in LeadersAdminView (e33f6b6)

### Bug Fixes
* fix(ci): remove trailing spaces and fix markdown lint issues (d06e62b)
* fix(ci): add timezone import and enhance quality-check skills (fe58787)
* fix(ci): fix release workflow issues (1866464)
* fix(ci): complete rewrite of release workflow with conventional commits (1f8cd3b)
* fix(ci): switch to tag-based releases (b18d75c)
* fix(ci): add skip-release-pulls parameter directly to workflow (330e9e7)
* fix(ci): enable automatic releases on push to main (e07d439)
* fix(ci): change release workflow trigger from push to workflow_dispatch (d24686b)
* fix: remove ignore (074ebdb)
* fix: synchronize active district selection across admin views (8a46758)

### Other Changes
* build(deps-dev): Bump eslint from 10.0.3 to 10.2.1 in /services/frontend (#88) (f0a5bc5)
* chore: release v0.2.9 (698f1b3)
* build(deps): Update pydantic[email] requirement in /services/backend (#89) (572b7ef)
* chore: release v0.2.8 (ea072cf)
* build(deps): Bump authlib (#91) (8a9119f)
* chore: release v0.2.7 (fd60fe3)
* build(deps): Update celery[sqlalchemy] requirement in /services/backend (#86) (3c8fed3)
* chore: release v0.2.6 (fbfa5af)
* build(deps): Bump actions/checkout from 4 to 6 (#85) (0bd1ef6)
* chore: release v0.2.5 (c03a9f8)

## [v0.2.9] - 2026-04-19

### Features
* feat: add checks skill for code quality verification (eadd177)
* feat: add pluggable IDP provisioning layer (63d5e66)
* feat: add approval-based IDP onboarding and pending alerts (06b84c3)
* feat: add openspec configuration for auto-generating 8-week draft services (a0565a6)
* feat: add OpenSpec for approved IDP onboarding (ffe095a)
* feat: group congregations and sync district selection (ef51686)
* feat: optimize matrix view for wider, denser planning (0c0ca94)
* feat: add draft generation and matrix move workflow (e45f958)
* feat: add event-based invitation workflow in service matrix (6875958)
* feat: add state variables for self-linking leaders in LeadersAdminView (e33f6b6)

### Bug Fixes
* fix(ci): remove trailing spaces and fix markdown lint issues (d06e62b)
* fix(ci): add timezone import and enhance quality-check skills (fe58787)
* fix(ci): fix release workflow issues (1866464)
* fix(ci): complete rewrite of release workflow with conventional commits (1f8cd3b)
* fix(ci): switch to tag-based releases (b18d75c)
* fix(ci): add skip-release-pulls parameter directly to workflow (330e9e7)
* fix(ci): enable automatic releases on push to main (e07d439)
* fix(ci): change release workflow trigger from push to workflow_dispatch (d24686b)
* fix: remove ignore (074ebdb)
* fix: synchronize active district selection across admin views (8a46758)

### Other Changes
* build(deps): Update pydantic[email] requirement in /services/backend (#89) (572b7ef)
* chore: release v0.2.8 (ea072cf)
* build(deps): Bump authlib (#91) (8a9119f)
* chore: release v0.2.7 (fd60fe3)
* build(deps): Update celery[sqlalchemy] requirement in /services/backend (#86) (3c8fed3)
* chore: release v0.2.6 (fbfa5af)
* build(deps): Bump actions/checkout from 4 to 6 (#85) (0bd1ef6)
* chore: release v0.2.5 (c03a9f8)
* build(deps): Bump actions/setup-node from 4 to 6 (#84) (5951602)
* chore: release v0.2.4 (3947c9b)

## [v0.2.8] - 2026-04-19

### Features
* feat: add checks skill for code quality verification (eadd177)
* feat: add pluggable IDP provisioning layer (63d5e66)
* feat: add approval-based IDP onboarding and pending alerts (06b84c3)
* feat: add openspec configuration for auto-generating 8-week draft services (a0565a6)
* feat: add OpenSpec for approved IDP onboarding (ffe095a)
* feat: group congregations and sync district selection (ef51686)
* feat: optimize matrix view for wider, denser planning (0c0ca94)
* feat: add draft generation and matrix move workflow (e45f958)
* feat: add event-based invitation workflow in service matrix (6875958)
* feat: add state variables for self-linking leaders in LeadersAdminView (e33f6b6)

### Bug Fixes
* fix(ci): remove trailing spaces and fix markdown lint issues (d06e62b)
* fix(ci): add timezone import and enhance quality-check skills (fe58787)
* fix(ci): fix release workflow issues (1866464)
* fix(ci): complete rewrite of release workflow with conventional commits (1f8cd3b)
* fix(ci): switch to tag-based releases (b18d75c)
* fix(ci): add skip-release-pulls parameter directly to workflow (330e9e7)
* fix(ci): enable automatic releases on push to main (e07d439)
* fix(ci): change release workflow trigger from push to workflow_dispatch (d24686b)
* fix: remove ignore (074ebdb)
* fix: synchronize active district selection across admin views (8a46758)

### Other Changes
* build(deps): Bump authlib (#91) (8a9119f)
* chore: release v0.2.7 (fd60fe3)
* build(deps): Update celery[sqlalchemy] requirement in /services/backend (#86) (3c8fed3)
* chore: release v0.2.6 (fbfa5af)
* build(deps): Bump actions/checkout from 4 to 6 (#85) (0bd1ef6)
* chore: release v0.2.5 (c03a9f8)
* build(deps): Bump actions/setup-node from 4 to 6 (#84) (5951602)
* chore: release v0.2.4 (3947c9b)
* build(deps): Update passlib[bcrypt] requirement in /services/backend (#82) (a6a5657)
* chore: release v0.2.3 (bb58188)

## [v0.2.7] - 2026-04-19

### Features
* feat: add checks skill for code quality verification (eadd177)
* feat: add pluggable IDP provisioning layer (63d5e66)
* feat: add approval-based IDP onboarding and pending alerts (06b84c3)
* feat: add openspec configuration for auto-generating 8-week draft services (a0565a6)
* feat: add OpenSpec for approved IDP onboarding (ffe095a)
* feat: group congregations and sync district selection (ef51686)
* feat: optimize matrix view for wider, denser planning (0c0ca94)
* feat: add draft generation and matrix move workflow (e45f958)
* feat: add event-based invitation workflow in service matrix (6875958)
* feat: add state variables for self-linking leaders in LeadersAdminView (e33f6b6)

### Bug Fixes
* fix(ci): remove trailing spaces and fix markdown lint issues (d06e62b)
* fix(ci): add timezone import and enhance quality-check skills (fe58787)
* fix(ci): fix release workflow issues (1866464)
* fix(ci): complete rewrite of release workflow with conventional commits (1f8cd3b)
* fix(ci): switch to tag-based releases (b18d75c)
* fix(ci): add skip-release-pulls parameter directly to workflow (330e9e7)
* fix(ci): enable automatic releases on push to main (e07d439)
* fix(ci): change release workflow trigger from push to workflow_dispatch (d24686b)
* fix: remove ignore (074ebdb)
* fix: synchronize active district selection across admin views (8a46758)

### Other Changes
* build(deps): Update celery[sqlalchemy] requirement in /services/backend (#86) (3c8fed3)
* chore: release v0.2.6 (fbfa5af)
* build(deps): Bump actions/checkout from 4 to 6 (#85) (0bd1ef6)
* chore: release v0.2.5 (c03a9f8)
* build(deps): Bump actions/setup-node from 4 to 6 (#84) (5951602)
* chore: release v0.2.4 (3947c9b)
* build(deps): Update passlib[bcrypt] requirement in /services/backend (#82) (a6a5657)
* chore: release v0.2.3 (bb58188)
* build(deps): Bump vue from 3.5.31 to 3.5.32 in /services/frontend (#81) (240511c)
* chore: release v0.2.2 (fa81fa1)

## [v0.2.6] - 2026-04-19

### Features
* feat: add checks skill for code quality verification (eadd177)
* feat: add pluggable IDP provisioning layer (63d5e66)
* feat: add approval-based IDP onboarding and pending alerts (06b84c3)
* feat: add openspec configuration for auto-generating 8-week draft services (a0565a6)
* feat: add OpenSpec for approved IDP onboarding (ffe095a)
* feat: group congregations and sync district selection (ef51686)
* feat: optimize matrix view for wider, denser planning (0c0ca94)
* feat: add draft generation and matrix move workflow (e45f958)
* feat: add event-based invitation workflow in service matrix (6875958)
* feat: add state variables for self-linking leaders in LeadersAdminView (e33f6b6)

### Bug Fixes
* fix(ci): remove trailing spaces and fix markdown lint issues (d06e62b)
* fix(ci): add timezone import and enhance quality-check skills (fe58787)
* fix(ci): fix release workflow issues (1866464)
* fix(ci): complete rewrite of release workflow with conventional commits (1f8cd3b)
* fix(ci): switch to tag-based releases (b18d75c)
* fix(ci): add skip-release-pulls parameter directly to workflow (330e9e7)
* fix(ci): enable automatic releases on push to main (e07d439)
* fix(ci): change release workflow trigger from push to workflow_dispatch (d24686b)
* fix: remove ignore (074ebdb)
* fix: synchronize active district selection across admin views (8a46758)

### Other Changes
* build(deps): Bump actions/checkout from 4 to 6 (#85) (0bd1ef6)
* chore: release v0.2.5 (c03a9f8)
* build(deps): Bump actions/setup-node from 4 to 6 (#84) (5951602)
* chore: release v0.2.4 (3947c9b)
* build(deps): Update passlib[bcrypt] requirement in /services/backend (#82) (a6a5657)
* chore: release v0.2.3 (bb58188)
* build(deps): Bump vue from 3.5.31 to 3.5.32 in /services/frontend (#81) (240511c)
* chore: release v0.2.2 (fa81fa1)
* build(deps-dev): Bump happy-dom in /services/frontend (#79) (4ef4445)
* chore: release v0.2.1 (7f1f6af)

## [v0.2.5] - 2026-04-19

### Features
* feat: add checks skill for code quality verification (eadd177)
* feat: add pluggable IDP provisioning layer (63d5e66)
* feat: add approval-based IDP onboarding and pending alerts (06b84c3)
* feat: add openspec configuration for auto-generating 8-week draft services (a0565a6)
* feat: add OpenSpec for approved IDP onboarding (ffe095a)
* feat: group congregations and sync district selection (ef51686)
* feat: optimize matrix view for wider, denser planning (0c0ca94)
* feat: add draft generation and matrix move workflow (e45f958)
* feat: add event-based invitation workflow in service matrix (6875958)
* feat: add state variables for self-linking leaders in LeadersAdminView (e33f6b6)

### Bug Fixes
* fix(ci): remove trailing spaces and fix markdown lint issues (d06e62b)
* fix(ci): add timezone import and enhance quality-check skills (fe58787)
* fix(ci): fix release workflow issues (1866464)
* fix(ci): complete rewrite of release workflow with conventional commits (1f8cd3b)
* fix(ci): switch to tag-based releases (b18d75c)
* fix(ci): add skip-release-pulls parameter directly to workflow (330e9e7)
* fix(ci): enable automatic releases on push to main (e07d439)
* fix(ci): change release workflow trigger from push to workflow_dispatch (d24686b)
* fix: remove ignore (074ebdb)
* fix: synchronize active district selection across admin views (8a46758)

### Other Changes
* build(deps): Bump actions/setup-node from 4 to 6 (#84) (5951602)
* chore: release v0.2.4 (3947c9b)
* build(deps): Update passlib[bcrypt] requirement in /services/backend (#82) (a6a5657)
* chore: release v0.2.3 (bb58188)
* build(deps): Bump vue from 3.5.31 to 3.5.32 in /services/frontend (#81) (240511c)
* chore: release v0.2.2 (fa81fa1)
* build(deps-dev): Bump happy-dom in /services/frontend (#79) (4ef4445)
* chore: release v0.2.1 (7f1f6af)
* build(deps-dev): Bump pytest from 9.0.2 to 9.0.3 in /services/backend (#71) (9f8c92b)
* chore: release v0.2.0 (0b05755)

## [v0.2.4] - 2026-04-19

### Features
* feat: add checks skill for code quality verification (eadd177)
* feat: add pluggable IDP provisioning layer (63d5e66)
* feat: add approval-based IDP onboarding and pending alerts (06b84c3)
* feat: add openspec configuration for auto-generating 8-week draft services (a0565a6)
* feat: add OpenSpec for approved IDP onboarding (ffe095a)
* feat: group congregations and sync district selection (ef51686)
* feat: optimize matrix view for wider, denser planning (0c0ca94)
* feat: add draft generation and matrix move workflow (e45f958)
* feat: add event-based invitation workflow in service matrix (6875958)
* feat: add state variables for self-linking leaders in LeadersAdminView (e33f6b6)

### Bug Fixes
* fix(ci): remove trailing spaces and fix markdown lint issues (d06e62b)
* fix(ci): add timezone import and enhance quality-check skills (fe58787)
* fix(ci): fix release workflow issues (1866464)
* fix(ci): complete rewrite of release workflow with conventional commits (1f8cd3b)
* fix(ci): switch to tag-based releases (b18d75c)
* fix(ci): add skip-release-pulls parameter directly to workflow (330e9e7)
* fix(ci): enable automatic releases on push to main (e07d439)
* fix(ci): change release workflow trigger from push to workflow_dispatch (d24686b)
* fix: remove ignore (074ebdb)
* fix: synchronize active district selection across admin views (8a46758)

### Other Changes
* build(deps): Update passlib[bcrypt] requirement in /services/backend (#82) (a6a5657)
* chore: release v0.2.3 (bb58188)
* build(deps): Bump vue from 3.5.31 to 3.5.32 in /services/frontend (#81) (240511c)
* chore: release v0.2.2 (fa81fa1)
* build(deps-dev): Bump happy-dom in /services/frontend (#79) (4ef4445)
* chore: release v0.2.1 (7f1f6af)
* build(deps-dev): Bump pytest from 9.0.2 to 9.0.3 in /services/backend (#71) (9f8c92b)
* chore: release v0.2.0 (0b05755)
* chore: release v0.1.3 (3fd5b7e)
* Merge branch 'main' of github.com:stritti/nak-district-planner (2cd035f)

## [v0.2.3] - 2026-04-19

### Features
* feat: add checks skill for code quality verification (eadd177)
* feat: add pluggable IDP provisioning layer (63d5e66)
* feat: add approval-based IDP onboarding and pending alerts (06b84c3)
* feat: add openspec configuration for auto-generating 8-week draft services (a0565a6)
* feat: add OpenSpec for approved IDP onboarding (ffe095a)
* feat: group congregations and sync district selection (ef51686)
* feat: optimize matrix view for wider, denser planning (0c0ca94)
* feat: add draft generation and matrix move workflow (e45f958)
* feat: add event-based invitation workflow in service matrix (6875958)
* feat: add state variables for self-linking leaders in LeadersAdminView (e33f6b6)

### Bug Fixes
* fix(ci): remove trailing spaces and fix markdown lint issues (d06e62b)
* fix(ci): add timezone import and enhance quality-check skills (fe58787)
* fix(ci): fix release workflow issues (1866464)
* fix(ci): complete rewrite of release workflow with conventional commits (1f8cd3b)
* fix(ci): switch to tag-based releases (b18d75c)
* fix(ci): add skip-release-pulls parameter directly to workflow (330e9e7)
* fix(ci): enable automatic releases on push to main (e07d439)
* fix(ci): change release workflow trigger from push to workflow_dispatch (d24686b)
* fix: remove ignore (074ebdb)
* fix: synchronize active district selection across admin views (8a46758)

### Other Changes
* build(deps): Bump vue from 3.5.31 to 3.5.32 in /services/frontend (#81) (240511c)
* chore: release v0.2.2 (fa81fa1)
* build(deps-dev): Bump happy-dom in /services/frontend (#79) (4ef4445)
* chore: release v0.2.1 (7f1f6af)
* build(deps-dev): Bump pytest from 9.0.2 to 9.0.3 in /services/backend (#71) (9f8c92b)
* chore: release v0.2.0 (0b05755)
* chore: release v0.1.3 (3fd5b7e)
* Merge branch 'main' of github.com:stritti/nak-district-planner (2cd035f)
* docs: expand developer guide with installation, environment usage, and security aspects (0b606c7)
* chore: release v0.1.2 (f5abcc4)

## [v0.2.2] - 2026-04-19

### Features
* feat: add checks skill for code quality verification (eadd177)
* feat: add pluggable IDP provisioning layer (63d5e66)
* feat: add approval-based IDP onboarding and pending alerts (06b84c3)
* feat: add openspec configuration for auto-generating 8-week draft services (a0565a6)
* feat: add OpenSpec for approved IDP onboarding (ffe095a)
* feat: group congregations and sync district selection (ef51686)
* feat: optimize matrix view for wider, denser planning (0c0ca94)
* feat: add draft generation and matrix move workflow (e45f958)
* feat: add event-based invitation workflow in service matrix (6875958)
* feat: add state variables for self-linking leaders in LeadersAdminView (e33f6b6)

### Bug Fixes
* fix(ci): remove trailing spaces and fix markdown lint issues (d06e62b)
* fix(ci): add timezone import and enhance quality-check skills (fe58787)
* fix(ci): fix release workflow issues (1866464)
* fix(ci): complete rewrite of release workflow with conventional commits (1f8cd3b)
* fix(ci): switch to tag-based releases (b18d75c)
* fix(ci): add skip-release-pulls parameter directly to workflow (330e9e7)
* fix(ci): enable automatic releases on push to main (e07d439)
* fix(ci): change release workflow trigger from push to workflow_dispatch (d24686b)
* fix: remove ignore (074ebdb)
* fix: synchronize active district selection across admin views (8a46758)

### Other Changes
* build(deps-dev): Bump happy-dom in /services/frontend (#79) (4ef4445)
* chore: release v0.2.1 (7f1f6af)
* build(deps-dev): Bump pytest from 9.0.2 to 9.0.3 in /services/backend (#71) (9f8c92b)
* chore: release v0.2.0 (0b05755)
* chore: release v0.1.3 (3fd5b7e)
* Merge branch 'main' of github.com:stritti/nak-district-planner (2cd035f)
* docs: expand developer guide with installation, environment usage, and security aspects (0b606c7)
* chore: release v0.1.2 (f5abcc4)
* chore: release v0.1.1 (06b51a0)
* chore: release v0.1.0 (0b81fb3)

## [v0.2.1] - 2026-04-19

### Features
* feat: add checks skill for code quality verification (eadd177)
* feat: add pluggable IDP provisioning layer (63d5e66)
* feat: add approval-based IDP onboarding and pending alerts (06b84c3)
* feat: add openspec configuration for auto-generating 8-week draft services (a0565a6)
* feat: add OpenSpec for approved IDP onboarding (ffe095a)
* feat: group congregations and sync district selection (ef51686)
* feat: optimize matrix view for wider, denser planning (0c0ca94)
* feat: add draft generation and matrix move workflow (e45f958)
* feat: add event-based invitation workflow in service matrix (6875958)
* feat: add state variables for self-linking leaders in LeadersAdminView (e33f6b6)

### Bug Fixes
* fix(ci): remove trailing spaces and fix markdown lint issues (d06e62b)
* fix(ci): add timezone import and enhance quality-check skills (fe58787)
* fix(ci): fix release workflow issues (1866464)
* fix(ci): complete rewrite of release workflow with conventional commits (1f8cd3b)
* fix(ci): switch to tag-based releases (b18d75c)
* fix(ci): add skip-release-pulls parameter directly to workflow (330e9e7)
* fix(ci): enable automatic releases on push to main (e07d439)
* fix(ci): change release workflow trigger from push to workflow_dispatch (d24686b)
* fix: remove ignore (074ebdb)
* fix: synchronize active district selection across admin views (8a46758)

### Other Changes
* build(deps-dev): Bump pytest from 9.0.2 to 9.0.3 in /services/backend (#71) (9f8c92b)
* chore: release v0.2.0 (0b05755)
* chore: release v0.1.3 (3fd5b7e)
* Merge branch 'main' of github.com:stritti/nak-district-planner (2cd035f)
* docs: expand developer guide with installation, environment usage, and security aspects (0b606c7)
* chore: release v0.1.2 (f5abcc4)
* chore: release v0.1.1 (06b51a0)
* chore: release v0.1.0 (0b81fb3)
* chore: remove unused release-please configuration (5ce1982)
* cleanup: remove obsolete test scripts, empty __init__.py files, and unused imports (b817225)

## [v0.2.0] - 2026-04-17

### Features
* feat: add checks skill for code quality verification (eadd177)
* feat: add pluggable IDP provisioning layer (63d5e66)
* feat: add approval-based IDP onboarding and pending alerts (06b84c3)
* feat: add openspec configuration for auto-generating 8-week draft services (a0565a6)
* feat: add OpenSpec for approved IDP onboarding (ffe095a)
* feat: group congregations and sync district selection (ef51686)
* feat: optimize matrix view for wider, denser planning (0c0ca94)
* feat: add draft generation and matrix move workflow (e45f958)
* feat: add event-based invitation workflow in service matrix (6875958)
* feat: add state variables for self-linking leaders in LeadersAdminView (e33f6b6)

### Bug Fixes
* fix(ci): remove trailing spaces and fix markdown lint issues (d06e62b)
* fix(ci): add timezone import and enhance quality-check skills (fe58787)
* fix(ci): fix release workflow issues (1866464)
* fix(ci): complete rewrite of release workflow with conventional commits (1f8cd3b)
* fix(ci): switch to tag-based releases (b18d75c)
* fix(ci): add skip-release-pulls parameter directly to workflow (330e9e7)
* fix(ci): enable automatic releases on push to main (e07d439)
* fix(ci): change release workflow trigger from push to workflow_dispatch (d24686b)
* fix: remove ignore (074ebdb)
* fix: synchronize active district selection across admin views (8a46758)

### Other Changes
* chore: release v0.1.3 (3fd5b7e)
* Merge branch 'main' of github.com:stritti/nak-district-planner (2cd035f)
* docs: expand developer guide with installation, environment usage, and security aspects (0b606c7)
* chore: release v0.1.2 (f5abcc4)
* chore: release v0.1.1 (06b51a0)
* chore: release v0.1.0 (0b81fb3)
* chore: remove unused release-please configuration (5ce1982)
* cleanup: remove obsolete test scripts, empty __init__.py files, and unused imports (b817225)
* Add project-checks skill and ruff/vue-tsc dependencies (d876312)
* build(deps): Bump authlib from 1.6.9 to 1.6.10 in /services/backend (#78) (221a984)

## [v0.1.3] - 2026-04-17

### Features
* feat: add pluggable IDP provisioning layer (63d5e66)
* feat: add approval-based IDP onboarding and pending alerts (06b84c3)
* feat: add openspec configuration for auto-generating 8-week draft services (a0565a6)
* feat: add OpenSpec for approved IDP onboarding (ffe095a)
* feat: group congregations and sync district selection (ef51686)
* feat: optimize matrix view for wider, denser planning (0c0ca94)
* feat: add draft generation and matrix move workflow (e45f958)
* feat: add event-based invitation workflow in service matrix (6875958)
* feat: add state variables for self-linking leaders in LeadersAdminView (e33f6b6)
* feat: enhance OIDC authentication with multi-strategy token validation and configurable logging (441acb8)

### Bug Fixes
* fix(ci): remove trailing spaces and fix markdown lint issues (d06e62b)
* fix(ci): add timezone import and enhance quality-check skills (fe58787)
* fix(ci): fix release workflow issues (1866464)
* fix(ci): complete rewrite of release workflow with conventional commits (1f8cd3b)
* fix(ci): switch to tag-based releases (b18d75c)
* fix(ci): add skip-release-pulls parameter directly to workflow (330e9e7)
* fix(ci): enable automatic releases on push to main (e07d439)
* fix(ci): change release workflow trigger from push to workflow_dispatch (d24686b)
* fix: remove ignore (074ebdb)
* fix: synchronize active district selection across admin views (8a46758)

### Other Changes
* Merge branch 'main' of github.com:stritti/nak-district-planner (2cd035f)
* docs: expand developer guide with installation, environment usage, and security aspects (0b606c7)
* chore: release v0.1.2 (f5abcc4)
* chore: release v0.1.1 (06b51a0)
* chore: release v0.1.0 (0b81fb3)
* chore: remove unused release-please configuration (5ce1982)
* cleanup: remove obsolete test scripts, empty __init__.py files, and unused imports (b817225)
* Add project-checks skill and ruff/vue-tsc dependencies (d876312)
* build(deps): Bump authlib from 1.6.9 to 1.6.10 in /services/backend (#78) (221a984)
* build(deps-dev): Bump @vitejs/plugin-vue in /services/frontend (#75) (00d9649)

## [v0.1.2] - 2026-04-16

### Features
* feat: add pluggable IDP provisioning layer (63d5e66)
* feat: add approval-based IDP onboarding and pending alerts (06b84c3)
* feat: add openspec configuration for auto-generating 8-week draft services (a0565a6)
* feat: add OpenSpec for approved IDP onboarding (ffe095a)
* feat: group congregations and sync district selection (ef51686)
* feat: optimize matrix view for wider, denser planning (0c0ca94)
* feat: add draft generation and matrix move workflow (e45f958)
* feat: add event-based invitation workflow in service matrix (6875958)
* feat: add state variables for self-linking leaders in LeadersAdminView (e33f6b6)
* feat: enhance OIDC authentication with multi-strategy token validation and configurable logging (441acb8)

### Bug Fixes
* fix(ci): remove trailing spaces and fix markdown lint issues (d06e62b)
* fix(ci): add timezone import and enhance quality-check skills (fe58787)
* fix(ci): fix release workflow issues (1866464)
* fix(ci): complete rewrite of release workflow with conventional commits (1f8cd3b)
* fix(ci): switch to tag-based releases (b18d75c)
* fix(ci): add skip-release-pulls parameter directly to workflow (330e9e7)
* fix(ci): enable automatic releases on push to main (e07d439)
* fix(ci): change release workflow trigger from push to workflow_dispatch (d24686b)
* fix: remove ignore (074ebdb)
* fix: synchronize active district selection across admin views (8a46758)

### Other Changes
* chore: release v0.1.1 (06b51a0)
* chore: release v0.1.0 (0b81fb3)
* chore: remove unused release-please configuration (5ce1982)
* cleanup: remove obsolete test scripts, empty __init__.py files, and unused imports (b817225)
* Add project-checks skill and ruff/vue-tsc dependencies (d876312)
* build(deps): Bump authlib from 1.6.9 to 1.6.10 in /services/backend (#78) (221a984)
* build(deps-dev): Bump @vitejs/plugin-vue in /services/frontend (#75) (00d9649)
* build(deps-dev): Update setuptools requirement in /services/backend (#76) (5cdb2d0)
* build(deps-dev): Bump typescript-eslint in /services/frontend (#74) (0a0b536)
* chore: standardize markdown formatting and update documentation references across the repository (a75b6a9)

## [v0.1.1] - 2026-04-16

### Features
* feat: add pluggable IDP provisioning layer (63d5e66)
* feat: add approval-based IDP onboarding and pending alerts (06b84c3)
* feat: add openspec configuration for auto-generating 8-week draft services (a0565a6)
* feat: add OpenSpec for approved IDP onboarding (ffe095a)
* feat: group congregations and sync district selection (ef51686)
* feat: optimize matrix view for wider, denser planning (0c0ca94)
* feat: add draft generation and matrix move workflow (e45f958)
* feat: add event-based invitation workflow in service matrix (6875958)
* feat: add state variables for self-linking leaders in LeadersAdminView (e33f6b6)
* feat: enhance OIDC authentication with multi-strategy token validation and configurable logging (441acb8)

### Bug Fixes
* fix(ci): add timezone import and enhance quality-check skills (fe58787)
* fix(ci): fix release workflow issues (1866464)
* fix(ci): complete rewrite of release workflow with conventional commits (1f8cd3b)
* fix(ci): switch to tag-based releases (b18d75c)
* fix(ci): add skip-release-pulls parameter directly to workflow (330e9e7)
* fix(ci): enable automatic releases on push to main (e07d439)
* fix(ci): change release workflow trigger from push to workflow_dispatch (d24686b)
* fix: remove ignore (074ebdb)
* fix: synchronize active district selection across admin views (8a46758)
* fix: allow replacing and clearing matrix assignments (9ff2072)

### Other Changes
* chore: release v0.1.0 (0b81fb3)
* chore: remove unused release-please configuration (5ce1982)
* cleanup: remove obsolete test scripts, empty __init__.py files, and unused imports (b817225)
* Add project-checks skill and ruff/vue-tsc dependencies (d876312)
* build(deps): Bump authlib from 1.6.9 to 1.6.10 in /services/backend (#78) (221a984)
* build(deps-dev): Bump @vitejs/plugin-vue in /services/frontend (#75) (00d9649)
* build(deps-dev): Update setuptools requirement in /services/backend (#76) (5cdb2d0)
* build(deps-dev): Bump typescript-eslint in /services/frontend (#74) (0a0b536)
* chore: standardize markdown formatting and update documentation references across the repository (a75b6a9)
* chore: clean up whitespace and update yamllint configuration (ba4f5bf)

## [v0.1.0] - 2026-04-16

### Features
* feat: add pluggable IDP provisioning layer (63d5e66)
* feat: add approval-based IDP onboarding and pending alerts (06b84c3)
* feat: add openspec configuration for auto-generating 8-week draft services (a0565a6)
* feat: add OpenSpec for approved IDP onboarding (ffe095a)
* feat: group congregations and sync district selection (ef51686)
* feat: optimize matrix view for wider, denser planning (0c0ca94)
* feat: add draft generation and matrix move workflow (e45f958)
* feat: add event-based invitation workflow in service matrix (6875958)
* feat: add state variables for self-linking leaders in LeadersAdminView (e33f6b6)
* feat: enhance OIDC authentication with multi-strategy token validation and configurable logging (441acb8)

### Bug Fixes
* fix(ci): fix release workflow issues (1866464)
* fix(ci): complete rewrite of release workflow with conventional commits (1f8cd3b)
* fix(ci): switch to tag-based releases (b18d75c)
* fix(ci): add skip-release-pulls parameter directly to workflow (330e9e7)
* fix(ci): enable automatic releases on push to main (e07d439)
* fix(ci): change release workflow trigger from push to workflow_dispatch (d24686b)
* fix: remove ignore (074ebdb)
* fix: synchronize active district selection across admin views (8a46758)
* fix: allow replacing and clearing matrix assignments (9ff2072)
* fix(release): use PAT token for release-please and opt into Node.js 24 (#61) (29ceb22)

### Other Changes
* chore: remove unused release-please configuration (5ce1982)
* cleanup: remove obsolete test scripts, empty __init__.py files, and unused imports (b817225)
* Add project-checks skill and ruff/vue-tsc dependencies (d876312)
* build(deps): Bump authlib from 1.6.9 to 1.6.10 in /services/backend (#78) (221a984)
* build(deps-dev): Bump @vitejs/plugin-vue in /services/frontend (#75) (00d9649)
* build(deps-dev): Update setuptools requirement in /services/backend (#76) (5cdb2d0)
* build(deps-dev): Bump typescript-eslint in /services/frontend (#74) (0a0b536)
* chore: standardize markdown formatting and update documentation references across the repository (a75b6a9)
* chore: clean up whitespace and update yamllint configuration (ba4f5bf)
* chore: update release-please token to use GITHUB_TOKEN (3936d60)

# Changelog
