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
