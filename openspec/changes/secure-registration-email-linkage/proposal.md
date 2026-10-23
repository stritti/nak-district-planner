## Why
Authenticated public registrations currently trust an arbitrary submitted email while binding the token's `sub` directly. A subsequent administrator approval can attach a membership to a different account than the claimed email owner, bypassing verified-email login linkage. See #708.

## What Changes
- Require an explicitly verified matching email from validated OIDC claims for the direct `sub` binding.
- Reject unverified or mismatching authenticated registrations with HTTP 403.
- Preserve anonymous registration and invalid-token behavior.
- Add unit and PostgreSQL RLS regression tests and update the onboarding documentation.

## Capabilities
### Modified Capabilities
- `approved-user-onboarding`: tighten the registration linkage identity contract.

## Impact
- Backend registration route, tests and onboarding documentation; no database migration or new dependencies.
