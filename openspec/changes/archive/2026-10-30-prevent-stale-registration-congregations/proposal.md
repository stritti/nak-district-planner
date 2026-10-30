## Why
The registration page may show congregations from a previously selected district because Vue watcher responses are not ordered. This can cause misleading choices and avoidable server-side validation errors. See #712.

## What Changes
- Invalidate asynchronous congregation loads as soon as the district changes or is cleared.
- Clear old congregation choices immediately; accept only the currently selected district's result.
- Keep prior server-side district and role authorization checks unchanged.
- Add deterministic race-condition and stale-failure regression tests.

## Capabilities
### Modified Capabilities
- `frontend-ux`: preserve the district-scoped registration form state under concurrent requests.

## Impact
Only Vue registration UI, tests and OpenSpec. No API or database migration.
