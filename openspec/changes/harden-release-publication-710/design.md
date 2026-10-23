## Context

Release Please creates the GitHub Release and tag before release notes or Docker builds. GitHub/GHCR do not provide an atomic multi-package transaction.

## Decisions

1. Use Release Please `draft: true` plus `force-tag-creation: true` so release history and its previous tag are available while the public release stays hidden.
2. Validate the release tag, ancestry on `main`, draft status and actionable upgrade notes before builds.
3. Use two sequential Buildx candidate pushes from the same tagged checkout, producing independent digests. Release promotion starts only when both complete.
4. Verify staged image digests before writing either exact version tag. Existing version tags are never repointed. Verify each resulting tag digest.
5. Promote stable aliases (`major.minor`, `major`, `latest`) only after both exact tags have been created; prereleases skip aliases. Serialize release runs using GitHub Actions concurrency.
6. Record previous aliases and restore them on registry promotion or GitHub publication failure where an earlier alias exists. Aliases without a previous tag require manual recovery.
7. Publish the GitHub Release only after both images, notes and aliases are ready. Add `workflow_dispatch` for explicit retries of an existing draft, without rerunning release-please.

## Trade-offs

- Tags in two GHCR repositories cannot move atomically. All production deployments use exact `APP_VERSION` rather than aliases; temporary alias skew remains possible.
- Partial version-tag promotion can survive failures. Retried builds with different digests deliberately fail closed and require manual recovery using the original digest.
- Force-created Git tags are visible before the draft is published; only published GitHub Releases signal availability.

