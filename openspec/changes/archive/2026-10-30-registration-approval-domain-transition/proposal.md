## Why
Registration approval mutates twelve domain fields in the FastAPI HTTP adapter instead of through the LeaderRegistration domain model. This mixes transport and domain concerns and complicates exception-path testing. First bounded step of #714.

## What Changes
- Move the approval status and authorization metadata transition to `LeaderRegistration.approve`.
- Fail closed on attempts to approve a non-pending registration; do not mutate any state in that case.
- Preserve leader persistence, membership linkage, IDP provisioning and after-commit events in existing route.
- Add unit regression tests for assigned state, error path and UTC timestamp.

## Capabilities
### Modified Capabilities
- `approved-user-onboarding`: domain transition remains atomic and requires pending state.

## Impact
Backend domain model, registration router and unit tests. No DB migration or public API change.
