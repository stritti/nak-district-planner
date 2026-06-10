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
