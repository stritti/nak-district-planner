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
