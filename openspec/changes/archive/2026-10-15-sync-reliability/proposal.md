# Sync reliability (#470)

Persist failed calendar sync attempts independently of the provider-write transaction, prevent overlapping runs from consuming worker slots, and move Celery off the experimental SQLAlchemy broker to Valkey.

## Scope
- Persist `last_attempt_at` for both scheduled and manual execution; report secret-safe `last_sync_error` after rollback.
- Skip busy integrations via `pg_try_advisory_xact_lock`.
- Suppress redundant periodic dispatches during retry backoff.
- Use Valkey Redis-compatible Celery transport and bounded execution.

## Constraints
- Successful event import remains atomic.
- Provider error bodies and credentials must never be persisted.
- Schema migration must be applied before workers start.
