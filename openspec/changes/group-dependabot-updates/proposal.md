## Why

Dependabot currently opens mostly individual updates across the frontend, documentation and backend. Grouping related routine updates reduces review noise while keeping major upgrades and unrelated container changes independently reviewable.

## What Changes

- Group patch/minor version updates into GitHub Actions (apart from CodeQL), frontend runtime, build, testing and linting, documentation, and backend API, database, telemetry, tooling and remaining runtime dependencies.
- Preserve the existing CodeQL group for all version levels so init/analyze remain on the same action version.
- Explicitly scope new groups to version updates; preserve security-update behavior.
- Preserve weekly schedules, all seven ecosystem/directory entries, Docker behavior and the Python image minor/major ignore rule.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `ci-supply-chain`: Related Dependabot version updates are grouped with explicit major-update and CodeQL exceptions.

## Impact

Only `.github/dependabot.yml` and this OpenSpec change are modified. No application code, dependency versions, lockfiles, CI gates, auto-merge workflow or repository settings change. Application coverage requirements remain enforced by the existing CI; this configuration change introduces no executable code.

Reference: [GitHub Dependabot groups](https://docs.github.com/en/code-security/reference/supply-chain-security/dependabot-options-reference#groups).
