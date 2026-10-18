# Durable Audit Outbox Design

## Intent and baseline

Protect forensic traceability under a 24/7 workload while preserving tenant isolation and Clean Code boundaries. Today `AuditedSession` records many audited aggregate changes in `audit_logs` inside `after_flush`; it has a separate path for bulk operations. In contrast, `AuditMiddleware` places HTTP-level audit records in an unbounded in-memory queue, after a route may already have committed and returned. The writer can lose a dequeued event after a session-open, tenant-GUC or commit error.

## Design decisions

### 1. Commit boundary, not the response middleware

The reliable acceptance boundary is the business transaction. Change the domain audit hook from direct final-table insertion to immutable `audit_outbox` intent insertion on that *same* SQLAlchemy connection. If insert, tenant context or commit fails, the business write rolls back and the API does not return success. Explicit bulk operations use the same outbox repository within their transaction. An audit bypass caused by an unresolved tenant is a hard error for required audited resources, not a warning followed by a skip.

A route inventory identifies all security-relevant write entrypoints, including non-ORM SQL writes and external side effects. Each must either join a transaction carrying an outbox intent or persist an intent before irreversible side effects. A post-response middleware record must never be represented as a transactional guarantee. Route and worker paths that cannot prove this are not enabled for fail-closed production writes until adapted and covered by tests.

### 2. Outbox schema, tenancy and idempotency

Create `audit_outbox` with immutable `event_id UUID` (PK), a bounded, redacted `payload JSONB`, tenant identity, `created_at`, `attempts`, `next_attempt_at`, and processing state. Unique `event_id` is propagated unchanged to `audit_logs.id`. Each dispatch inserts with conflict handling on that ID and removes/marks the outbox entry in the same database transaction. This gives at-least-once delivery attempts but exactly one visible audit row per event, even after consumer crashes.

Database migration sets RLS and least-privilege grants for the application role and a narrowly scoped system-worker path. The worker must not accidentally read or process another tenant outside its defined security context. Old `audit_logs` rows remain valid and queryable; there is no destructive backfill.

### 3. Dispatcher and bounded failure behavior

Implement a persistent poller/worker using `FOR UPDATE SKIP LOCKED`; no in-memory unbounded retry queue. Batch size <= 100, bounded concurrent workers, exponential backoff capped at 5 minutes with jitter, and configurable polling cadence. Transient failure retains the event in PostgreSQL with `attempts` and the next attempt time; poison events enter a visible quarantine state, not silent deletion. Redacted, rate-limited error logs never serialize event payloads.

On normal shutdown stop claiming new rows and finish the current batch up to 10 seconds; remaining rows stay in the database. A hard crash leaves rows for another worker. Use a transaction-scoped claim: no permanent lease is required. A sustained PostgreSQL outage causes security-relevant writes to fail and produces health/alert signals; no RAM growth.

### 4. HTTP audit and non-mutating denials

Retire the lossy asynchronous queue as a durability mechanism. Non-mutating denials and failed unauthenticated requests cannot be rolled into a nonexistent business transaction, so their HTTP audit uses a *synchronous durable insert* before returning a final response. If PostgreSQL is unavailable, expose a safe service error and an operational alert; do not return an unaudited 403 while claiming reliable audit. Where a write route already has a transactional domain audit, avoid duplicate semantically identical events; distinct HTTP events use distinct stable IDs and sources.

Audit availability is a separate health signal, not a substitute for enforcing failure at the write transaction boundary.

### 5. Verification and rollout

Add deterministic unit tests for routing and idempotency plus real PostgreSQL integration tests for insert/commit failure, session creation failure, tenant GUC rejection, rollback, outbox replay after restart, duplicate worker claims, poison-event handling and bounded shutdown. Verify no non-transactional success responses on failure. Maintain backend coverage >= 80% and add the regression suite to CI. Migration must be safe for fresh installs and upgrades, include a documented rollback/restore plan and production alerts for outbox backlog, oldest age, retries and quarantine count.

## Alternatives rejected

- Memory retry queue: cannot survive process crashes, unbounded memory or missing delivery can silently lose evidence.
- Logging HTTP requests only in middleware: happens after a business transaction and cannot undo a committed change.
- Remote broker as the sole acceptance path: would not be atomic with PostgreSQL domain writes.

## Constraints and risks

There is no generic post-commit mechanism to make a previously committed write fail-closed. Coverage of *all* security-relevant routes must be proven from an explicit inventory before declaring global guarantees. Audit fields follow existing redaction conventions. A PostgreSQL outage intentionally reduces write availability.
