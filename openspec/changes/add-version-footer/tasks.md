## 1. Frontend

- [x] 1.1 Inject the frontend version from `package.json` at build time (`__APP_VERSION__`)
- [x] 1.2 `buildInfo` store reads the backend version from public `GET /api/health` with plain `fetch`
- [x] 1.3 `AppFooter` shows both versions on every page, `–` when the backend version is unknown

## 2. Verification

- [x] 2.1 Unit tests: store (success, 503, invalid payloads, network failure, no credentials) and footer
- [x] 2.2 Built bundle contains the package version; footer checked in a real browser, signed out, with the backend reachable and unreachable
