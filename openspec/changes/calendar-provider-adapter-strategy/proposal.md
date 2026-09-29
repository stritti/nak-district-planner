## Why

Google and Microsoft calendar adapters currently implement protocol details directly with httpx. PR #375 adds necessary pagination and retry hardening, but long-term maintainability also requires an explicit provider-adapter strategy for token refresh, pagination, throttling, error normalization, and SDK upgrades.

## What Changes

- Define a stable provider-neutral CalendarConnector port and provider adapter contract.
- Evaluate official/established Google and Microsoft SDKs behind adapters instead of exposing SDK types to application/domain code.
- Centralize transient retry/throttling policy for idempotent reads.
- Define pagination completeness, credential refresh, timeout, and error-normalization requirements.
- Add contract tests shared by provider adapters.

## Capabilities

### New Capabilities
- `calendar-provider-adapter-contract`
- `calendar-provider-resilience`

### Modified Capabilities
- `calendar-sync`

## Impact

- Google and Microsoft adapters only; domain/application contracts remain provider neutral.
- Dependency footprint may change after explicit SDK evaluation.
- No behavioral regression in sync semantics is permitted.
