# ci-quality-gates Delta

## MODIFIED Requirements

### Requirement: Documentation and OpenSpec gate
The `docs` workflow SHALL run on every pull request to `main`, strictly validate all baseline specifications and active changes with a pinned OpenSpec CLI using `validate --all --strict --no-interactive`, and build the VitePress site from the root lockfile.

#### Scenario: Invalid active spec delta
- **WHEN** a pull request contains an invalid active OpenSpec change
- **THEN** the existing required `Build documentation` status fails

#### Scenario: Valid baseline and active changes
- **WHEN** all baseline specifications and active changes validate strictly
- **THEN** the documentation build continues with frozen dependencies
