## Why

Dependabot updates frequently introduce mergeable patch/minor changes whose checks are already enforced by the active `main` ruleset. Manual merges create unnecessary delay. However, an unattended merge must not bypass security audits, coverage, current-base checks or the requirement that only Dependabot-generated code is eligible.

## What Changes

- Add a SHA-pinned, privileged metadata-only `pull_request_target` workflow.
- Enable GitHub native auto-merge exclusively for verified Dependabot patch/minor updates targeting `main`.
- Keep major, unclassified, draft and maintainer-modified updates subject to manual review.
- Do not check out or execute PR code with elevated permissions; use job-scoped token rights.
- Rely on the existing strict `main` ruleset and its required status checks for the actual merge.

## Capabilities

### Modified Capabilities

- `ci-supply-chain`: Dependabot auto-merge is tightly scoped to verified non-major updates.
- `ci-quality-gates`: An automatic merge cannot bypass the required quality gates.

## Impact

- After enabling the repository's **Settings → General → Pull Requests → Allow auto-merge** option, eligible future Dependabot PRs are scheduled for squash merge.
- Repository option `allow_auto_merge` is currently **false** and cannot be enabled from a repository file alone; enabling it is an explicit administrative prerequisite.
- Every failing, pending or outdated required CI check continues to block merging.
