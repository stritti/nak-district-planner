# Implementation checklist for #474

- [x] Use a plain CSRF header helper in HTTP calls
- [x] Preserve form input on CSRF-403 errors
- [x] Add public 404 route with regression coverage
- [x] Honor configured duration in MatrixService
- [x] Replace component-local CSS with Tailwind utilities
- [x] Remove unused SyncStatusCard and OIDC build-time examples
- [x] Remove unregistered Celery tasks
- [x] Remove unused passlib dependency and lock entries
- [x] Centralize provider event fingerprints
- [x] Consolidate API/Beat series generation
- [x] Move Celery entrypoints under inbound adapters
- [x] Decouple application services from API schemas
- [x] Verify unit, integration, build and coverage gates
- [x] Require authenticated Codecov uploads and surface missing-token warnings without weakening local coverage gates
- [x] Correct worker use-case wiring and verify the manual planning generator constructor
- [x] Anchor multi-interval recurrences to the series and restore worship-service defaults
- [x] Use runtime duration settings and typed calendar commands with explicit DTO mapping
- [x] Convert the not-found view to a Vue SFC and extend regression coverage

- [x] Reject malformed recurrence intervals at API boundaries and isolate invalid legacy series in the worker batch
