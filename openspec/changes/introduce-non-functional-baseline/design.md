## Context

The system includes planning governance, bidirectional calendar synchronization, token-based exports, and user-scoped authorization. Without explicit non-functional requirements, system behavior under load, failure, or misuse is undefined.

## Goals / Non-Goals

**Goals:**
- Define measurable performance targets.
- Define explicit security constraints.
- Define mandatory audit logging events.
- Define operational monitoring and retry policies.

**Non-Goals:**
- Implementation of specific monitoring vendors.
- Advanced distributed tracing architecture.

## Decisions

### 1. Performance Baseline
- Matrix API latency SHALL be ≤ 500ms for typical district scope (≤ 50 congregations, 3 months view).
- Sync job SHALL complete within configurable timeout (default 5 minutes per integration).
- Both are measured against PostgreSQL with active RLS (`tests/performance`, results in `docs/performance-baseline.md`).

### 2. Security Baseline
- All credentials SHALL be encrypted at rest.
- Export tokens SHALL be cryptographically secure and at least 128-bit entropy.
- Rate limiting SHALL apply to public export endpoints.

### 3. Audit Logging
Audit log entries SHALL be created for:
- PlanningSlot creation/modification/deletion
- ServiceAssignment changes
- CalendarIntegration creation/modification/deletion
- Token creation/revocation

**Implementation: persistence hook instead of event bus.** Domain audit entries are written by an SQLAlchemy `after_flush` listener on the application session (`app/adapters/db/domain_audit.py`), not via the `DomainEventBus` of `event-driven-mail-hooks`:
- *Transactional:* the entry is inserted on the flushing connection, so it exists exactly when the change commits; a rollback leaves no entry. The bus publishes after commit and would lose entries on a crash in between.
- *Complete:* every ORM write is covered, including Celery tasks (actor `system:celery-worker`), without each use case having to emit events. Bulk statements bypass the unit of work; the retention cleanup therefore writes one `BULK_OPERATION` entry itself.
- *RLS-safe:* the entry carries the row's district and congregation. Every actor allowed to write an audited row satisfies the `audit_logs` insert policy; entries without a resolvable tenant are skipped with a warning rather than aborting the business transaction.
- *No secrets:* only whitelisted fields are snapshotted; `credentials_enc` and the export token value appear by name in `changes.redacted_fields`. Sync bookkeeping (`last_synced_at`, `last_sync_error`) is not audited.
- The HTTP `AuditMiddleware` stays as the request-level trail; domain entries are marked `extra_metadata.source = "domain"`.

### 4. Operational Requirements
- Sync failures SHALL trigger structured logs.
- Repeated failures SHALL emit alert events.
- Retry with exponential backoff SHALL be applied for transient errors.

## Risks / Trade-offs

[Over-specification] → Keep baseline measurable but minimal.
[Operational Complexity] → Phase implementation with feature flags.

## Migration Plan

1. Introduce audit_log table.
2. Introduce rate limiting middleware.
3. Add structured logging to sync jobs.
4. Validate performance targets in staging.

Rollback: Disable enforcement checks while retaining logging.
