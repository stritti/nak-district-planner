## Why
Existing Keycloak provisioning installations cannot boot after switching to self-registration without an operational migration, yet release-please lists onboarding as an ordinary minor-version feature. Operators need an unmistakable breaking-change warning before an attempted 1.6.0 upgrade. See #713.

## What Changes
- Make Keycloak 1.6.0 upgrade instructions explicitly identify the incompatible configuration.
- Promote any operator note marked `**Breaking Change:**` above generated changelog using a conspicuous banner.
- Validate the real Keycloak note and banner handling via repeatable Docs CI tests.
- Document mandatory manual Keycloak/SMTP/RBAC/rollback checks.

## Capabilities
### Modified Capabilities
- `production-deployment`: operators are warned before starting incompatible deployments.

## Impact
Release notes, documentation, publisher and script unit tests. No Keycloak behavior or database changes.
