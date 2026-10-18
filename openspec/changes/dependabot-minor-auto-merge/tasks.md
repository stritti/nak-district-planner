## 1. Safe classification and merge

- [x] 1.1 Add SHA-pinned Dependabot metadata verification without checking out pull-request code.
- [x] 1.2 Limit eligibility to non-draft, genuine Dependabot patch/minor updates against `main`.
- [x] 1.3 Use GitHub-native auto-merge instead of bypassing the ruleset.
- [x] 1.4 Preserve job-level least-privilege permissions.

## 2. Specifications and validation

- [x] 2.1 Specify eligible updates, excluded cases and failure behavior in OpenSpec.
- [ ] 2.2 Verify workflow lint, OpenSpec validation and repository CI after opening the pull request.
- [ ] 2.3 Enable **Allow auto-merge** in the GitHub repository settings (requires repository administration).
- [ ] 2.4 Verify an eligible Dependabot PR is automatically merged only after all required checks succeed.
