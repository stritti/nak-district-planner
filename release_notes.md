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
