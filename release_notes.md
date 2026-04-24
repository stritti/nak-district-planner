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
