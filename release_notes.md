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
