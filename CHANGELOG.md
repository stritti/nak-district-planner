## [v0.19.0] - 2026-06-20

### Features
* Merge pull request #185 from stritti/feat/toast-confirm-dialogs (8a50676)
* Merge pull request #184 from stritti/feat/health-check-endpoint (9a5df96)
* Merge pull request #174 from stritti/feature/matrix-rendering-migration-1-1 (55355e8)
* Merge pull request #169 from stritti/feature/security-csrf-protection-sec-004 (55fb297)
* Merge pull request #154 from stritti/feat/p0-blitzer-production-readiness (8220231)
* feat(security): implement CSRF protection (SEC-004) (36a14c8)
* feat: add toast notification system and confirm dialog component (a300ac5)
* feat: add database health check to /api/health endpoint (52df2a9)
* feat: add database migration for PlanningSlot and Invitation new fields (c5b4beb)
* feat: migrate matrix rendering to use only PlanningSlot/EventInstance (Task 1.1) (52d74f1)

### Bug Fixes
* Fix duplicate starlette dependency and update requests version (e376147)
* Fix frontend tests: replace @vueuse/integrations with native cookie handling (cc29b50)
* Fix frontend tests: add js-cookie dependency and mock useCSRF in tests (317b9aa)
* Fix MegaLinter markdown issues in CSRF documentation (4a9088b)
* Fix CSRF token parsing bug for session-bound tokens (c445d9c)
* fix: health endpoint always returns ok status, update test (481856f)
* chore: update pydantic-settings to 2.14.2 to fix security vulnerability GHSA-4xgf-cpjx-pc3j (59c326a)
* fix: set event_id to slot.id for frontend compatibility (7a7ffbb)
* fix: add pytest import to feiertage_service tests (a37491e)
* fix: adjust RBAC guard for /access endpoint to allow PENDING_APPROVAL users (df3d466)

### Other Changes
* chore: release v0.18.0 (eea4ae3)
* chore: release v0.17.0 (769c3e8)
* chore: release v0.16.0 (2c8b5ec)
* chore: release v0.15.0 (5640fc2)
* Merge pull request #181 from stritti/dependabot/uv/services/backend/fastapi-0.138.0 (9678d97)
* Merge pull request #180 from stritti/dependabot/uv/services/backend/pytest-9.1.1 (bc754c6)
* Merge pull request #179 from stritti/dependabot/bun/services/frontend/happy-dom-20.10.6 (f582106)
* Merge pull request #178 from stritti/dependabot/uv/services/backend/ruff-0.15.18 (83ba7ce)
* Merge pull request #177 from stritti/dependabot/github_actions/actions/upload-artifact-7 (ee63451)
* chore: release v0.14.4 (2135e23)

## [v0.18.0] - 2026-06-20

### Features
* Merge pull request #184 from stritti/feat/health-check-endpoint (9a5df96)
* Merge pull request #174 from stritti/feature/matrix-rendering-migration-1-1 (55355e8)
* Merge pull request #169 from stritti/feature/security-csrf-protection-sec-004 (55fb297)
* Merge pull request #154 from stritti/feat/p0-blitzer-production-readiness (8220231)
* feat(security): implement CSRF protection (SEC-004) (36a14c8)
* feat: add database health check to /api/health endpoint (52df2a9)
* feat: add database migration for PlanningSlot and Invitation new fields (c5b4beb)
* feat: migrate matrix rendering to use only PlanningSlot/EventInstance (Task 1.1) (52d74f1)
* feat: add missing fields to PlanningSlot and Invitation models for matrix migration (c8441dd)
* Merge pull request #170 from stritti/feature/rbac-completion-1-4 (4ac8a98)

### Bug Fixes
* Fix duplicate starlette dependency and update requests version (e376147)
* Fix frontend tests: replace @vueuse/integrations with native cookie handling (cc29b50)
* Fix frontend tests: add js-cookie dependency and mock useCSRF in tests (317b9aa)
* Fix MegaLinter markdown issues in CSRF documentation (4a9088b)
* Fix CSRF token parsing bug for session-bound tokens (c445d9c)
* fix: health endpoint always returns ok status, update test (481856f)
* chore: update pydantic-settings to 2.14.2 to fix security vulnerability GHSA-4xgf-cpjx-pc3j (59c326a)
* fix: set event_id to slot.id for frontend compatibility (7a7ffbb)
* fix: add pytest import to feiertage_service tests (a37491e)
* fix: adjust RBAC guard for /access endpoint to allow PENDING_APPROVAL users (df3d466)

### Other Changes
* chore: release v0.17.0 (769c3e8)
* chore: release v0.16.0 (2c8b5ec)
* chore: release v0.15.0 (5640fc2)
* Merge pull request #181 from stritti/dependabot/uv/services/backend/fastapi-0.138.0 (9678d97)
* Merge pull request #180 from stritti/dependabot/uv/services/backend/pytest-9.1.1 (bc754c6)
* Merge pull request #179 from stritti/dependabot/bun/services/frontend/happy-dom-20.10.6 (f582106)
* Merge pull request #178 from stritti/dependabot/uv/services/backend/ruff-0.15.18 (83ba7ce)
* Merge pull request #177 from stritti/dependabot/github_actions/actions/upload-artifact-7 (ee63451)
* chore: release v0.14.4 (2135e23)
* Merge pull request #175 from stritti/dependabot/github_actions/actions/checkout-7 (ab23b8d)

## [v0.17.0] - 2026-06-20

### Features
* Merge pull request #174 from stritti/feature/matrix-rendering-migration-1-1 (55355e8)
* Merge pull request #169 from stritti/feature/security-csrf-protection-sec-004 (55fb297)
* Merge pull request #154 from stritti/feat/p0-blitzer-production-readiness (8220231)
* feat(security): implement CSRF protection (SEC-004) (36a14c8)
* feat: add database migration for PlanningSlot and Invitation new fields (c5b4beb)
* feat: migrate matrix rendering to use only PlanningSlot/EventInstance (Task 1.1) (52d74f1)
* feat: add missing fields to PlanningSlot and Invitation models for matrix migration (c8441dd)
* Merge pull request #170 from stritti/feature/rbac-completion-1-4 (4ac8a98)
* feat: add RBAC guards to auth.py and system.py routers (Task 1.4) (9e677d2)
* feat: OpenSpec Spezifikationen für Security Issues (20f5b2e)

### Bug Fixes
* Fix duplicate starlette dependency and update requests version (e376147)
* Fix frontend tests: replace @vueuse/integrations with native cookie handling (cc29b50)
* Fix frontend tests: add js-cookie dependency and mock useCSRF in tests (317b9aa)
* Fix MegaLinter markdown issues in CSRF documentation (4a9088b)
* Fix CSRF token parsing bug for session-bound tokens (c445d9c)
* chore: update pydantic-settings to 2.14.2 to fix security vulnerability GHSA-4xgf-cpjx-pc3j (59c326a)
* fix: set event_id to slot.id for frontend compatibility (7a7ffbb)
* fix: add pytest import to feiertage_service tests (a37491e)
* fix: adjust RBAC guard for /access endpoint to allow PENDING_APPROVAL users (df3d466)
* fix: rename status variable to avoid shadowing fastapi.status import (9250f5d)

### Other Changes
* chore: release v0.16.0 (2c8b5ec)
* chore: release v0.15.0 (5640fc2)
* Merge pull request #181 from stritti/dependabot/uv/services/backend/fastapi-0.138.0 (9678d97)
* Merge pull request #180 from stritti/dependabot/uv/services/backend/pytest-9.1.1 (bc754c6)
* Merge pull request #179 from stritti/dependabot/bun/services/frontend/happy-dom-20.10.6 (f582106)
* Merge pull request #178 from stritti/dependabot/uv/services/backend/ruff-0.15.18 (83ba7ce)
* Merge pull request #177 from stritti/dependabot/github_actions/actions/upload-artifact-7 (ee63451)
* chore: release v0.14.4 (2135e23)
* Merge pull request #175 from stritti/dependabot/github_actions/actions/checkout-7 (ab23b8d)
* chore: release v0.14.3 (ea78759)

## [v0.16.0] - 2026-06-20

### Features
* Merge pull request #169 from stritti/feature/security-csrf-protection-sec-004 (55fb297)
* Merge pull request #154 from stritti/feat/p0-blitzer-production-readiness (8220231)
* feat(security): implement CSRF protection (SEC-004) (36a14c8)
* Merge pull request #170 from stritti/feature/rbac-completion-1-4 (4ac8a98)
* feat: add RBAC guards to auth.py and system.py routers (Task 1.4) (9e677d2)
* feat: OpenSpec Spezifikationen für Security Issues (20f5b2e)
* feat: umfassende Security-Analyse und Dokumentationserweiterungen (18c36bf)
* Merge pull request #162 from stritti/feat/e2e-and-coverage (3c969dc)
* Merge pull request #153 from stritti/feat/e2e-and-coverage (3badc13)
* Merge branch 'main' into feat/e2e-and-coverage (23c5702)

### Bug Fixes
* Fix duplicate starlette dependency and update requests version (e376147)
* Fix frontend tests: replace @vueuse/integrations with native cookie handling (cc29b50)
* Fix frontend tests: add js-cookie dependency and mock useCSRF in tests (317b9aa)
* Fix MegaLinter markdown issues in CSRF documentation (4a9088b)
* Fix CSRF token parsing bug for session-bound tokens (c445d9c)
* fix: adjust RBAC guard for /access endpoint to allow PENDING_APPROVAL users (df3d466)
* fix: rename status variable to avoid shadowing fastapi.status import (9250f5d)
* Fix markdownlint issues: add language specifiers to code blocks, wrap bare URLs, fix trailing spaces and newlines (052f542)
* Merge pull request #163 from stritti/copilot/fix-merge-konflikte-and-action-errors (07430ad)
* fix(e2e): add auth/calendar/component mocks and fix DistrictsAdminView error handling (344d745)

### Other Changes
* chore: release v0.15.0 (5640fc2)
* Merge pull request #181 from stritti/dependabot/uv/services/backend/fastapi-0.138.0 (9678d97)
* Merge pull request #180 from stritti/dependabot/uv/services/backend/pytest-9.1.1 (bc754c6)
* Merge pull request #179 from stritti/dependabot/bun/services/frontend/happy-dom-20.10.6 (f582106)
* Merge pull request #178 from stritti/dependabot/uv/services/backend/ruff-0.15.18 (83ba7ce)
* Merge pull request #177 from stritti/dependabot/github_actions/actions/upload-artifact-7 (ee63451)
* chore: release v0.14.4 (2135e23)
* Merge pull request #175 from stritti/dependabot/github_actions/actions/checkout-7 (ab23b8d)
* chore: release v0.14.3 (ea78759)
* Merge pull request #176 from stritti/dependabot/github_actions/astral-sh/setup-uv-7 (89ac858)

## [v0.15.0] - 2026-06-20

### Features
* Merge pull request #154 from stritti/feat/p0-blitzer-production-readiness (8220231)
* Merge pull request #170 from stritti/feature/rbac-completion-1-4 (4ac8a98)
* feat: add RBAC guards to auth.py and system.py routers (Task 1.4) (9e677d2)
* feat: OpenSpec Spezifikationen für Security Issues (20f5b2e)
* feat: umfassende Security-Analyse und Dokumentationserweiterungen (18c36bf)
* Merge pull request #162 from stritti/feat/e2e-and-coverage (3c969dc)
* Merge pull request #153 from stritti/feat/e2e-and-coverage (3badc13)
* Merge branch 'main' into feat/e2e-and-coverage (23c5702)
* feat: P0-Blitzer production readiness — production guard, permission audit, cross-tenant isolation (13eb0bd)
* feat(tests): add e2e tests and improve backend coverage to 82% (dda308e)

### Bug Fixes
* fix: adjust RBAC guard for /access endpoint to allow PENDING_APPROVAL users (df3d466)
* fix: rename status variable to avoid shadowing fastapi.status import (9250f5d)
* Fix markdownlint issues: add language specifiers to code blocks, wrap bare URLs, fix trailing spaces and newlines (052f542)
* Merge pull request #163 from stritti/copilot/fix-merge-konflikte-and-action-errors (07430ad)
* fix(e2e): add auth/calendar/component mocks and fix DistrictsAdminView error handling (344d745)
* Plan PR 141 merge fix (d520d6c)
* Merge pull request #161 from stritti/copilot/fix-review-issues (3d3451a)
* fix: address remaining Codex P1/P2 review findings (d533906)
* Merge pull request #160 from stritti/copilot/fix-issues (64932ff)
* fix(e2e): block service worker in Playwright to prevent route mock bypass (17e8bd1)

### Other Changes
* Merge pull request #181 from stritti/dependabot/uv/services/backend/fastapi-0.138.0 (9678d97)
* Merge pull request #180 from stritti/dependabot/uv/services/backend/pytest-9.1.1 (bc754c6)
* Merge pull request #179 from stritti/dependabot/bun/services/frontend/happy-dom-20.10.6 (f582106)
* Merge pull request #178 from stritti/dependabot/uv/services/backend/ruff-0.15.18 (83ba7ce)
* Merge pull request #177 from stritti/dependabot/github_actions/actions/upload-artifact-7 (ee63451)
* chore: release v0.14.4 (2135e23)
* Merge pull request #175 from stritti/dependabot/github_actions/actions/checkout-7 (ab23b8d)
* chore: release v0.14.3 (ea78759)
* Merge pull request #176 from stritti/dependabot/github_actions/astral-sh/setup-uv-7 (89ac858)
* chore: release v0.14.2 (aa01d67)

## [v0.14.4] - 2026-06-20

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
* Merge pull request #175 from stritti/dependabot/github_actions/actions/checkout-7 (ab23b8d)
* chore: release v0.14.3 (ea78759)
* Merge pull request #176 from stritti/dependabot/github_actions/astral-sh/setup-uv-7 (89ac858)
* chore: release v0.14.2 (aa01d67)
* Merge pull request #182 from stritti/dependabot/uv/services/backend/sqlalchemy-asyncio--gte-2.0.51 (69100c0)
* chore: release v0.14.1 (9e22bd3)
* Merge pull request #183 from stritti/dependabot/uv/services/backend/pydantic-settings-2.14.2 (5d5dddf)
* build(deps): Bump pydantic-settings in /services/backend (c7f4f16)
* build(deps): Update sqlalchemy[asyncio] requirement in /services/backend (a588c47)
* build(deps): Bump astral-sh/setup-uv from 5 to 7 (747b020)

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

## [v0.14.2] - 2026-06-20

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
* Merge pull request #182 from stritti/dependabot/uv/services/backend/sqlalchemy-asyncio--gte-2.0.51 (69100c0)
* chore: release v0.14.1 (9e22bd3)
* Merge pull request #183 from stritti/dependabot/uv/services/backend/pydantic-settings-2.14.2 (5d5dddf)
* build(deps): Bump pydantic-settings in /services/backend (c7f4f16)
* build(deps): Update sqlalchemy[asyncio] requirement in /services/backend (a588c47)
* chore: release v0.14.0 (aaf93f5)
* chore: release v0.13.0 (f724043)
* Merge pull request #167 from stritti/vibe/security-analysis-5ad88e (cb306cf)
* chore: release v0.12.6 (e7bcebf)
* Merge pull request #168 from stritti/vibe/openspec-gap-analysis-refined-71c667 (0731ee9)

## [v0.14.1] - 2026-06-20

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
* Merge pull request #183 from stritti/dependabot/uv/services/backend/pydantic-settings-2.14.2 (5d5dddf)
* build(deps): Bump pydantic-settings in /services/backend (c7f4f16)
* chore: release v0.14.0 (aaf93f5)
* chore: release v0.13.0 (f724043)
* Merge pull request #167 from stritti/vibe/security-analysis-5ad88e (cb306cf)
* chore: release v0.12.6 (e7bcebf)
* Merge pull request #168 from stritti/vibe/openspec-gap-analysis-refined-71c667 (0731ee9)
* docs: update OpenSpec specs and add implementation tasks (5ceb5b4)
* docs: add refined OpenSpec gap analysis v2.1 with domain expert confirmations (de6bbc7)
* chore: release v0.12.5 (a868a32)

## [v0.14.0] - 2026-06-19

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
* chore: release v0.13.0 (f724043)
* Merge pull request #167 from stritti/vibe/security-analysis-5ad88e (cb306cf)
* chore: release v0.12.6 (e7bcebf)
* Merge pull request #168 from stritti/vibe/openspec-gap-analysis-refined-71c667 (0731ee9)
* docs: update OpenSpec specs and add implementation tasks (5ceb5b4)
* docs: add refined OpenSpec gap analysis v2.1 with domain expert confirmations (de6bbc7)
* chore: release v0.12.5 (a868a32)
* chore: activate Mistral Vibe Code for OpenSpec (aa5ce32)
* chore: release v0.12.4 (dcf9e8f)
* Merge pull request #140 from stritti/dependabot/uv/services/backend/ruff-0.15.16 (35f8618)

## [v0.13.0] - 2026-06-19

### Features
* feat: OpenSpec Spezifikationen für Security Issues (20f5b2e)
* feat: umfassende Security-Analyse und Dokumentationserweiterungen (18c36bf)
* Merge pull request #162 from stritti/feat/e2e-and-coverage (3c969dc)
* Merge pull request #153 from stritti/feat/e2e-and-coverage (3badc13)
* Merge branch 'main' into feat/e2e-and-coverage (23c5702)
* feat(tests): add e2e tests and improve backend coverage to 82% (dda308e)
* feat: add pr-review skill for structured review comment handling (ec499a7)
* Merge pull request #152 from stritti/feat/responsive-pwa (e7c4c2c)
* feat: responsive UI + PWA support (d5f0bad)
* Merge pull request #150 from stritti/feat/approval-status (ee43e4e)

### Bug Fixes
* Fix markdownlint issues: add language specifiers to code blocks, wrap bare URLs, fix trailing spaces and newlines (052f542)
* Merge pull request #163 from stritti/copilot/fix-merge-konflikte-and-action-errors (07430ad)
* fix(e2e): add auth/calendar/component mocks and fix DistrictsAdminView error handling (344d745)
* Plan PR 141 merge fix (d520d6c)
* Merge pull request #160 from stritti/copilot/fix-issues (64932ff)
* fix(e2e): block service worker in Playwright to prevent route mock bypass (17e8bd1)
* Merge pull request #159 from stritti/copilot/fix-action-run-error (949924a)
* test: fix matrix e2e syntax (561e68a)
* Merge pull request #157 from stritti/copilot/fix-correct-issue-for-reference (f3380c8)
* fix: correct Playwright route handler ordering — catch-all first, specific mocks after (55e05be)

### Other Changes
* Merge pull request #167 from stritti/vibe/security-analysis-5ad88e (cb306cf)
* chore: release v0.12.6 (e7bcebf)
* Merge pull request #168 from stritti/vibe/openspec-gap-analysis-refined-71c667 (0731ee9)
* docs: update OpenSpec specs and add implementation tasks (5ceb5b4)
* docs: add refined OpenSpec gap analysis v2.1 with domain expert confirmations (de6bbc7)
* chore: release v0.12.5 (a868a32)
* chore: activate Mistral Vibe Code for OpenSpec (aa5ce32)
* chore: release v0.12.4 (dcf9e8f)
* Merge pull request #140 from stritti/dependabot/uv/services/backend/ruff-0.15.16 (35f8618)
* chore: release v0.12.3 (b96c3f9)

## [v0.12.6] - 2026-06-19

### Features
* Merge pull request #162 from stritti/feat/e2e-and-coverage (3c969dc)
* Merge pull request #153 from stritti/feat/e2e-and-coverage (3badc13)
* Merge branch 'main' into feat/e2e-and-coverage (23c5702)
* feat(tests): add e2e tests and improve backend coverage to 82% (dda308e)
* feat: add pr-review skill for structured review comment handling (ec499a7)
* Merge pull request #152 from stritti/feat/responsive-pwa (e7c4c2c)
* feat: responsive UI + PWA support (d5f0bad)
* Merge pull request #150 from stritti/feat/approval-status (ee43e4e)
* feat: complete approval_status UI and tests (d83782c)
* feat: add approval_status (PLANNED/CONFIRMED) orthogonal to EventStatus (37f13dc)

### Bug Fixes
* Merge pull request #163 from stritti/copilot/fix-merge-konflikte-and-action-errors (07430ad)
* fix(e2e): add auth/calendar/component mocks and fix DistrictsAdminView error handling (344d745)
* Plan PR 141 merge fix (d520d6c)
* Merge pull request #160 from stritti/copilot/fix-issues (64932ff)
* fix(e2e): block service worker in Playwright to prevent route mock bypass (17e8bd1)
* Merge pull request #159 from stritti/copilot/fix-action-run-error (949924a)
* test: fix matrix e2e syntax (561e68a)
* Merge pull request #157 from stritti/copilot/fix-correct-issue-for-reference (f3380c8)
* fix: correct Playwright route handler ordering — catch-all first, specific mocks after (55e05be)
* Merge pull request #156 from stritti/copilot/fix-reference-issue (b0be84b)

### Other Changes
* Merge pull request #168 from stritti/vibe/openspec-gap-analysis-refined-71c667 (0731ee9)
* docs: update OpenSpec specs and add implementation tasks (5ceb5b4)
* docs: add refined OpenSpec gap analysis v2.1 with domain expert confirmations (de6bbc7)
* chore: release v0.12.5 (a868a32)
* chore: activate Mistral Vibe Code for OpenSpec (aa5ce32)
* chore: release v0.12.4 (dcf9e8f)
* Merge pull request #140 from stritti/dependabot/uv/services/backend/ruff-0.15.16 (35f8618)
* chore: release v0.12.3 (b96c3f9)
* Merge pull request #165 from stritti/chore/megalinter-v9.5.0-config (a4e90a3)
* chore: configure MegaLinter v9.5.0 settings (1173a56)

## [v0.12.5] - 2026-06-19

### Features
* Merge pull request #162 from stritti/feat/e2e-and-coverage (3c969dc)
* Merge pull request #153 from stritti/feat/e2e-and-coverage (3badc13)
* Merge branch 'main' into feat/e2e-and-coverage (23c5702)
* feat(tests): add e2e tests and improve backend coverage to 82% (dda308e)
* feat: add pr-review skill for structured review comment handling (ec499a7)
* Merge pull request #152 from stritti/feat/responsive-pwa (e7c4c2c)
* feat: responsive UI + PWA support (d5f0bad)
* Merge pull request #150 from stritti/feat/approval-status (ee43e4e)
* feat: complete approval_status UI and tests (d83782c)
* feat: add approval_status (PLANNED/CONFIRMED) orthogonal to EventStatus (37f13dc)

### Bug Fixes
* Merge pull request #163 from stritti/copilot/fix-merge-konflikte-and-action-errors (07430ad)
* fix(e2e): add auth/calendar/component mocks and fix DistrictsAdminView error handling (344d745)
* Plan PR 141 merge fix (d520d6c)
* Merge pull request #160 from stritti/copilot/fix-issues (64932ff)
* fix(e2e): block service worker in Playwright to prevent route mock bypass (17e8bd1)
* Merge pull request #159 from stritti/copilot/fix-action-run-error (949924a)
* test: fix matrix e2e syntax (561e68a)
* Merge pull request #157 from stritti/copilot/fix-correct-issue-for-reference (f3380c8)
* fix: correct Playwright route handler ordering — catch-all first, specific mocks after (55e05be)
* Merge pull request #156 from stritti/copilot/fix-reference-issue (b0be84b)

### Other Changes
* chore: activate Mistral Vibe Code for OpenSpec (aa5ce32)
* chore: release v0.12.4 (dcf9e8f)
* Merge pull request #140 from stritti/dependabot/uv/services/backend/ruff-0.15.16 (35f8618)
* chore: release v0.12.3 (b96c3f9)
* Merge pull request #165 from stritti/chore/megalinter-v9.5.0-config (a4e90a3)
* chore: configure MegaLinter v9.5.0 settings (1173a56)
* build(deps-dev): Bump ruff from 0.15.14 to 0.15.17 in /services/backend (13e0923)
* chore: release v0.12.2 (cabe4aa)
* Merge pull request #141 from stritti/dependabot/bun/services/frontend/vitest-4.1.8 (2547d6d)
* chore: release v0.12.1 (80fa5a8)

## [v0.12.4] - 2026-06-18

### Features
* Merge pull request #162 from stritti/feat/e2e-and-coverage (3c969dc)
* Merge pull request #153 from stritti/feat/e2e-and-coverage (3badc13)
* Merge branch 'main' into feat/e2e-and-coverage (23c5702)
* feat(tests): add e2e tests and improve backend coverage to 82% (dda308e)
* feat: add pr-review skill for structured review comment handling (ec499a7)
* Merge pull request #152 from stritti/feat/responsive-pwa (e7c4c2c)
* feat: responsive UI + PWA support (d5f0bad)
* Merge pull request #150 from stritti/feat/approval-status (ee43e4e)
* feat: complete approval_status UI and tests (d83782c)
* feat: add approval_status (PLANNED/CONFIRMED) orthogonal to EventStatus (37f13dc)

### Bug Fixes
* Merge pull request #163 from stritti/copilot/fix-merge-konflikte-and-action-errors (07430ad)
* fix(e2e): add auth/calendar/component mocks and fix DistrictsAdminView error handling (344d745)
* Plan PR 141 merge fix (d520d6c)
* Merge pull request #160 from stritti/copilot/fix-issues (64932ff)
* fix(e2e): block service worker in Playwright to prevent route mock bypass (17e8bd1)
* Merge pull request #159 from stritti/copilot/fix-action-run-error (949924a)
* test: fix matrix e2e syntax (561e68a)
* Merge pull request #157 from stritti/copilot/fix-correct-issue-for-reference (f3380c8)
* fix: correct Playwright route handler ordering — catch-all first, specific mocks after (55e05be)
* Merge pull request #156 from stritti/copilot/fix-reference-issue (b0be84b)

### Other Changes
* Merge pull request #140 from stritti/dependabot/uv/services/backend/ruff-0.15.16 (35f8618)
* chore: release v0.12.3 (b96c3f9)
* Merge pull request #165 from stritti/chore/megalinter-v9.5.0-config (a4e90a3)
* chore: configure MegaLinter v9.5.0 settings (1173a56)
* build(deps-dev): Bump ruff from 0.15.14 to 0.15.17 in /services/backend (13e0923)
* chore: release v0.12.2 (cabe4aa)
* Merge pull request #141 from stritti/dependabot/bun/services/frontend/vitest-4.1.8 (2547d6d)
* chore: release v0.12.1 (80fa5a8)
* Validate PR 141 merge update (2c4149a)
* Resolve PR 141 merge conflict (90c731f)

## [v0.12.3] - 2026-06-18

### Features
* Merge pull request #162 from stritti/feat/e2e-and-coverage (3c969dc)
* Merge pull request #153 from stritti/feat/e2e-and-coverage (3badc13)
* Merge branch 'main' into feat/e2e-and-coverage (23c5702)
* feat(tests): add e2e tests and improve backend coverage to 82% (dda308e)
* feat: add pr-review skill for structured review comment handling (ec499a7)
* Merge pull request #152 from stritti/feat/responsive-pwa (e7c4c2c)
* feat: responsive UI + PWA support (d5f0bad)
* Merge pull request #150 from stritti/feat/approval-status (ee43e4e)
* feat: complete approval_status UI and tests (d83782c)
* feat: add approval_status (PLANNED/CONFIRMED) orthogonal to EventStatus (37f13dc)

### Bug Fixes
* Merge pull request #163 from stritti/copilot/fix-merge-konflikte-and-action-errors (07430ad)
* fix(e2e): add auth/calendar/component mocks and fix DistrictsAdminView error handling (344d745)
* Plan PR 141 merge fix (d520d6c)
* Merge pull request #160 from stritti/copilot/fix-issues (64932ff)
* fix(e2e): block service worker in Playwright to prevent route mock bypass (17e8bd1)
* Merge pull request #159 from stritti/copilot/fix-action-run-error (949924a)
* test: fix matrix e2e syntax (561e68a)
* Merge pull request #157 from stritti/copilot/fix-correct-issue-for-reference (f3380c8)
* fix: correct Playwright route handler ordering — catch-all first, specific mocks after (55e05be)
* Merge pull request #156 from stritti/copilot/fix-reference-issue (b0be84b)

### Other Changes
* Merge pull request #165 from stritti/chore/megalinter-v9.5.0-config (a4e90a3)
* chore: configure MegaLinter v9.5.0 settings (1173a56)
* chore: release v0.12.2 (cabe4aa)
* Merge pull request #141 from stritti/dependabot/bun/services/frontend/vitest-4.1.8 (2547d6d)
* chore: release v0.12.1 (80fa5a8)
* Validate PR 141 merge update (2c4149a)
* Resolve PR 141 merge conflict (90c731f)
* chore: release v0.12.0 (efa7b06)
* test: verify matrix updates after assignment (2aa4c23)
* test: remove tracked Playwright artifact (d6487e3)

## [v0.12.2] - 2026-06-17

### Features
* Merge pull request #162 from stritti/feat/e2e-and-coverage (3c969dc)
* Merge pull request #153 from stritti/feat/e2e-and-coverage (3badc13)
* Merge branch 'main' into feat/e2e-and-coverage (23c5702)
* feat(tests): add e2e tests and improve backend coverage to 82% (dda308e)
* feat: add pr-review skill for structured review comment handling (ec499a7)
* Merge pull request #152 from stritti/feat/responsive-pwa (e7c4c2c)
* feat: responsive UI + PWA support (d5f0bad)
* Merge pull request #150 from stritti/feat/approval-status (ee43e4e)
* feat: complete approval_status UI and tests (d83782c)
* feat: add approval_status (PLANNED/CONFIRMED) orthogonal to EventStatus (37f13dc)

### Bug Fixes
* Merge pull request #163 from stritti/copilot/fix-merge-konflikte-and-action-errors (07430ad)
* fix(e2e): add auth/calendar/component mocks and fix DistrictsAdminView error handling (344d745)
* Plan PR 141 merge fix (d520d6c)
* Merge pull request #160 from stritti/copilot/fix-issues (64932ff)
* fix(e2e): block service worker in Playwright to prevent route mock bypass (17e8bd1)
* Merge pull request #159 from stritti/copilot/fix-action-run-error (949924a)
* test: fix matrix e2e syntax (561e68a)
* Merge pull request #157 from stritti/copilot/fix-correct-issue-for-reference (f3380c8)
* fix: correct Playwright route handler ordering — catch-all first, specific mocks after (55e05be)
* Merge pull request #156 from stritti/copilot/fix-reference-issue (b0be84b)

### Other Changes
* Merge pull request #141 from stritti/dependabot/bun/services/frontend/vitest-4.1.8 (2547d6d)
* chore: release v0.12.1 (80fa5a8)
* Validate PR 141 merge update (2c4149a)
* Resolve PR 141 merge conflict (90c731f)
* chore: release v0.12.0 (efa7b06)
* test: verify matrix updates after assignment (2aa4c23)
* test: remove tracked Playwright artifact (d6487e3)
* test: stabilize frontend e2e assertions (c855e4a)
* test: stabilize failing e2e specs (e19c031)
* build(deps-dev): Bump vitest from 4.1.5 to 4.1.9 in /services/frontend (cb7a31c)

## [v0.12.1] - 2026-06-17

### Features
* Merge pull request #162 from stritti/feat/e2e-and-coverage (3c969dc)
* Merge pull request #153 from stritti/feat/e2e-and-coverage (3badc13)
* Merge branch 'main' into feat/e2e-and-coverage (23c5702)
* feat(tests): add e2e tests and improve backend coverage to 82% (dda308e)
* feat: add pr-review skill for structured review comment handling (ec499a7)
* Merge pull request #152 from stritti/feat/responsive-pwa (e7c4c2c)
* feat: responsive UI + PWA support (d5f0bad)
* Merge pull request #150 from stritti/feat/approval-status (ee43e4e)
* feat: complete approval_status UI and tests (d83782c)
* feat: add approval_status (PLANNED/CONFIRMED) orthogonal to EventStatus (37f13dc)

### Bug Fixes
* fix(e2e): add auth/calendar/component mocks and fix DistrictsAdminView error handling (344d745)
* Merge pull request #160 from stritti/copilot/fix-issues (64932ff)
* fix(e2e): block service worker in Playwright to prevent route mock bypass (17e8bd1)
* Merge pull request #159 from stritti/copilot/fix-action-run-error (949924a)
* test: fix matrix e2e syntax (561e68a)
* Merge pull request #157 from stritti/copilot/fix-correct-issue-for-reference (f3380c8)
* fix: correct Playwright route handler ordering — catch-all first, specific mocks after (55e05be)
* fix: e2e test failures - missing API mocks, wrong selectors, OIDC flow (25faafd)
* fix: vite preview port mismatch in Playwright webServer (92a6062)
* fix: ruff lint errors and formatting across backend (8831ada)

### Other Changes
* chore: release v0.12.0 (efa7b06)
* test: verify matrix updates after assignment (2aa4c23)
* test: remove tracked Playwright artifact (d6487e3)
* test: stabilize frontend e2e assertions (c855e4a)
* test: stabilize failing e2e specs (e19c031)
* Merge pull request #143 from stritti/dependabot/uv/services/backend/icalendar-7.1.2 (0679456)
* Merge pull request #142 from stritti/dependabot/bun/services/frontend/vue/test-utils-2.4.11 (58dc6dd)
* Merge pull request #144 from stritti/dependabot/bun/services/frontend/vue-router-5.1.0 (10cdf21)
* Merge pull request #145 from stritti/dependabot/uv/services/backend/pydantic-settings-2.14.1 (9802108)
* Merge pull request #146 from stritti/dependabot/uv/services/backend/uvicorn-standard--gte-0.49.0 (8e6c224)

## [v0.12.0] - 2026-06-16

### Features
* Merge pull request #153 from stritti/feat/e2e-and-coverage (3badc13)
* Merge branch 'main' into feat/e2e-and-coverage (23c5702)
* feat(tests): add e2e tests and improve backend coverage to 82% (dda308e)
* feat: add pr-review skill for structured review comment handling (ec499a7)
* Merge pull request #152 from stritti/feat/responsive-pwa (e7c4c2c)
* feat: responsive UI + PWA support (d5f0bad)
* Merge pull request #150 from stritti/feat/approval-status (ee43e4e)
* feat: complete approval_status UI and tests (d83782c)
* feat: add approval_status (PLANNED/CONFIRMED) orthogonal to EventStatus (37f13dc)
* feat: proxy OIDC token exchange through backend (76590c3)

### Bug Fixes
* Merge pull request #160 from stritti/copilot/fix-issues (64932ff)
* fix(e2e): block service worker in Playwright to prevent route mock bypass (17e8bd1)
* Merge pull request #159 from stritti/copilot/fix-action-run-error (949924a)
* test: fix matrix e2e syntax (561e68a)
* Merge pull request #157 from stritti/copilot/fix-correct-issue-for-reference (f3380c8)
* fix: correct Playwright route handler ordering — catch-all first, specific mocks after (55e05be)
* fix: e2e test failures - missing API mocks, wrong selectors, OIDC flow (25faafd)
* fix: vite preview port mismatch in Playwright webServer (92a6062)
* fix: ruff lint errors and formatting across backend (8831ada)
* fix: post coverage report as PR comment with threshold enforcement (c5d563a)

### Other Changes
* test: verify matrix updates after assignment (2aa4c23)
* test: remove tracked Playwright artifact (d6487e3)
* test: stabilize frontend e2e assertions (c855e4a)
* test: stabilize failing e2e specs (e19c031)
* Merge pull request #143 from stritti/dependabot/uv/services/backend/icalendar-7.1.2 (0679456)
* Merge pull request #142 from stritti/dependabot/bun/services/frontend/vue/test-utils-2.4.11 (58dc6dd)
* Merge pull request #144 from stritti/dependabot/bun/services/frontend/vue-router-5.1.0 (10cdf21)
* Merge pull request #145 from stritti/dependabot/uv/services/backend/pydantic-settings-2.14.1 (9802108)
* Merge pull request #146 from stritti/dependabot/uv/services/backend/uvicorn-standard--gte-0.49.0 (8e6c224)
* Merge pull request #147 from stritti/dependabot/uv/services/backend/pytest-asyncio-1.4.0 (57baf3d)

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
