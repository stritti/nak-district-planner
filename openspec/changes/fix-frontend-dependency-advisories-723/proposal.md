## Why
The GitHub Actions Security Scans workflow failed on `main` at commit `626c63dd` with three vulnerabilities: Happy DOM code injection (`GHSA-834v-8h66-3h79`, high) and two fast-uri validation advisories (`GHSA-w74x-v6f9-j3xg`, `GHSA-wjr9-j795-jxcr`, moderate).

## What Changes
- Upgrade the frontend direct development dependency `happy-dom` to the first fixed major release, `^21.0.4`, and pin its resolved version to 21.0.4 in the Bun lockfile.
- Upgrade the transitive dependency `fast-uri` to patched 3.1.9 within its existing dependency range.
- Preserve matching dependency metadata and tarball SHA-512 integrities in the frozen Bun lockfile.
- Keep the existing blocking `bun audit --audit-level=moderate` check unmodified.

## Capabilities
### Modified Capabilities
- `ci-quality-gates`: dependency audits continue rejecting vulnerable locked packages without exceptions.

## Impact
Only `services/frontend/package.json` and `services/frontend/bun.lock`, plus security upgrade specifications. No changes to production JavaScript, APIs or backend code. Tests and build must verify compatibility with Happy DOM 21.
