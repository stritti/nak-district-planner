## Security investigation
Frontend dependency graph on `main`:
- Direct dev dependency `happy-dom@20.14.5`, manifest `^20.14`. Affected by `GHSA-834v-8h66-3h79` for versions 17.0.0 through 21.0.3. First fixed version: 21.0.4.
- Transitive `fast-uri@3.1.8` from `eslint → ajv` and `vite-plugin-pwa → workbox-build → @apideck/better-ajv-errors → ajv`. Affected by `GHSA-w74x-v6f9-j3xg` and `GHSA-wjr9-j795-jxcr`; 3.1.9 fixes both.
- Independent failure verified on `main` in GitHub Actions [Security Scans #40086580700](https://github.com/stritti/nak-district-planner/actions/runs/40086580700), so this does not originate from the Python F401 work in issue #715.

## Decision
Apply the smallest compatible manifest/lockfile upgrade: `happy-dom ^21.0.4`, exact locked `happy-dom@21.0.4`, and exact locked `fast-uri@3.1.9`. The lock records the same upstream dependencies as the older Happy DOM version, and the published SHA512 integrity for each tarball. Only the frontend lock is relevant; the root `bun.lock` manages documentation and is not modified.

The lockfile contents for both patched versions and integrity digests were independently cross-checked against public Bun lockfiles (happy-dom: `leeoniya/uPlot` and `lidge-jun/opencodex`; fast-uri: `garrytan/gbrain` and `timescale/pg-aiguide`). The authoritative verification remains GitHub Actions' `bun install --frozen-lockfile`.

## Verification (RED–GREEN)
- **RED:** On main, security scan #40086580700 failed `bun audit --audit-level=moderate` (three advisories).
- **GREEN:** Re-run the unchanged audit on PR #725 with the corrected lockfile. It MUST report no moderate-or-higher advisories and return 0.
- Verify frozen installation, Vue/Vitest unit coverage (including negative-path tests), ESLint, production Vite/PWA build, Playwright E2E, and required backend integration/RLS/coverage workflows. Resolve any compatibility regressions rather than disabling a check.

## Rollback
Revert the dependency/lockfile commit only in concert with an alternative patched release; do not knowingly reintroduce vulnerable locked versions to clear a build. A blocked deployment is preferred to suppressing the audit.
