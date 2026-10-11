# Refactor planning and synchronization debt (#474)

## Why

The release review identified divergent slot generators, unregistered Celery tasks,
duplicate provider hashing, stale component styles, and destructive CSRF recovery.

## What Changes

- Consolidate slot generation behind one application implementation with UTC
  generation keys and deletion-ledger suppression for every caller.
- Keep scheduled jobs only when dispatched; place Celery entrypoints in inbound adapters.
- Centralize external event fingerprint calculation in synchronization.
- Preserve existing API contracts and tenant-scoped access checks.
- Prevent destructive reloads for recoverable HTTP 403 errors.
- Use Tailwind utilities, a public 404 route, and remove unused code and dependencies.

## Impact

No data migration. Existing drafts, event instances, suppression ledger, and
calendar integration records must retain their semantics.
