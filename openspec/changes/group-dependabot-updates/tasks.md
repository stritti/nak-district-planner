## 1. Group configuration

- [x] 1.1 Add related patch/minor groups for Actions, frontend, documentation and backend; verify every current manifest dependency matches exactly one intended group.
- [x] 1.2 Preserve CodeQL coupling and container settings; compare the parsed configuration with the original after removing newly added groups.
- [x] 1.3 Verify edge cases: major updates, security updates, unknown frontend packages, backend fallback exclusions and CodeQL init/analyze at every version level.

## 2. Validation and publication

- [x] 2.1 Validate the configuration against the Dependabot JSON schema and validate this OpenSpec change with CLI 1.14.1 in strict mode.
- [x] 2.2 Review the focused change against current main; verify only the Dependabot configuration and this OpenSpec change are included in the publication manifest.

## Workflow follow-up

- Publish the prepared pull request and verify its changed-file list and published configuration.

- After merge, inspect the next scheduled Dependabot run; hosted dependency resolution cannot be validated before the configuration reaches the default branch.
