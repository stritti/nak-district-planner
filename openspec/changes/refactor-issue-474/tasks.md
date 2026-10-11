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
- [ ] Verify unit, integration, build and coverage gates
