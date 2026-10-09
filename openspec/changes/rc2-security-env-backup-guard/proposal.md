# Prevent committed environment backups

## Why

RC-2 contains a tracked Keycloak environment backup with password-like values. Accidental inclusion of this file in the public repository is an avoidable credential-exposure risk.

## What Changes

- Remove the tracked local IdP backup.
- Ignore backup environment files in Git.
- Fail a required security CI job when tracked backups are present.
- Document the guard in the CI supply-chain baseline.

## Operational Considerations

Deletion does not purge the Git history. Any credentials used in a real environment require rotation outside this change. Do not log or reproduce values.
