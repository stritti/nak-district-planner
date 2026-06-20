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
