## [v0.14.3] - 2026-06-20

### Features
* Merge pull request #170 from stritti/feature/rbac-completion-1-4 (4ac8a98)
* feat: add RBAC guards to auth.py and system.py routers (Task 1.4) (9e677d2)
* feat: OpenSpec Spezifikationen für Security Issues (20f5b2e)
* feat: umfassende Security-Analyse und Dokumentationserweiterungen (18c36bf)
* Merge pull request #162 from stritti/feat/e2e-and-coverage (3c969dc)
* Merge pull request #153 from stritti/feat/e2e-and-coverage (3badc13)
* Merge branch 'main' into feat/e2e-and-coverage (23c5702)
* feat(tests): add e2e tests and improve backend coverage to 82% (dda308e)
* feat: add pr-review skill for structured review comment handling (ec499a7)
* Merge pull request #152 from stritti/feat/responsive-pwa (e7c4c2c)

### Bug Fixes
* fix: adjust RBAC guard for /access endpoint to allow PENDING_APPROVAL users (df3d466)
* fix: rename status variable to avoid shadowing fastapi.status import (9250f5d)
* Fix markdownlint issues: add language specifiers to code blocks, wrap bare URLs, fix trailing spaces and newlines (052f542)
* Merge pull request #163 from stritti/copilot/fix-merge-konflikte-and-action-errors (07430ad)
* fix(e2e): add auth/calendar/component mocks and fix DistrictsAdminView error handling (344d745)
* Plan PR 141 merge fix (d520d6c)
* Merge pull request #160 from stritti/copilot/fix-issues (64932ff)
* fix(e2e): block service worker in Playwright to prevent route mock bypass (17e8bd1)
* Merge pull request #159 from stritti/copilot/fix-action-run-error (949924a)
* test: fix matrix e2e syntax (561e68a)

### Other Changes
* Merge pull request #176 from stritti/dependabot/github_actions/astral-sh/setup-uv-7 (89ac858)
* chore: release v0.14.2 (aa01d67)
* Merge pull request #182 from stritti/dependabot/uv/services/backend/sqlalchemy-asyncio--gte-2.0.51 (69100c0)
* chore: release v0.14.1 (9e22bd3)
* Merge pull request #183 from stritti/dependabot/uv/services/backend/pydantic-settings-2.14.2 (5d5dddf)
* build(deps): Bump pydantic-settings in /services/backend (c7f4f16)
* build(deps): Update sqlalchemy[asyncio] requirement in /services/backend (a588c47)
* build(deps): Bump astral-sh/setup-uv from 5 to 7 (747b020)
* chore: release v0.14.0 (aaf93f5)
* chore: release v0.13.0 (f724043)
