## Why

When a login fails or a release is rolled out, operators and users cannot tell which build they are looking at: the browser may still run a cached frontend (service worker) while the backend is already updated, or the other way round. The only version display (`UpdateBanner`) needs an administrator session, so it does not exist exactly where it is needed, on the login page.

## What Changes

- A small, muted footer on every page shows `Frontend v<version> · Backend v<version>`, also while signed out.
- Frontend version: injected from `package.json` at build time (`__APP_VERSION__`, Vite `define`); release-please already bumps it with every release.
- Backend version: read from the existing public `GET /api/health` (field `version`). It already reports the version without authentication and is exempt from auth, tenant, CSRF and audit handling; no new endpoint or public surface is added.
- The request uses plain `fetch`, never `apiFetch`, so a failure cannot trigger a token refresh or logout. If the backend is unreachable or answers without a version, the footer shows `–`. A degraded backend (503) still reports its version.

## Impact

- Affected specs: `version-check-and-update` (ADDED requirement).
- Affected files: `services/frontend/{vite.config.ts,vitest.config.ts,src/env.d.ts,src/App.vue,src/stores/buildInfo.ts,src/components/AppFooter.vue}` and tests.
- No backend or API changes. The backend version was already public via `/api/health`.
