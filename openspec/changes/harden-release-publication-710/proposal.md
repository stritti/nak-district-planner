## Why

Release Please currently creates a public GitHub Release before mandatory upgrade instructions and backend/frontend GHCR images are available (#710). A failure leaves an advertised release without operational artifacts and may split mutable aliases between services.

## What Changes

- Create draft GitHub Releases with eager Git-tag creation; publish only after both container digests and the upgrade notes have passed validation.
- Push build candidates under unique run-scoped tags; promote both immutable version tags before moving stable aliases.
- Provide fail-closed checks, best-effort alias rollback and an explicit manual retry for partially completed drafts.
- Add regression tests and update the release process and production runbook.

## Impact

- Affected components: `.github/workflows/release.yml`, GHCR release publication, `release-please-config.json`, release-note publisher, documentation.
- No application API or database migration. Production continues pinning exact `APP_VERSION` tags.
- Git tags become visible while release drafts are pending; a tag alone is not a readiness signal.

