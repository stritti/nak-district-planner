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
