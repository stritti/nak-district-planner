## Why

The HTTP audit writer in `AuditService._writer` acknowledges items even after a failed PostgreSQL write, and the queue is process-local. A successful state-changing request can therefore lose its request audit during DB outages or process crashes. Issue #648 requires fail-closed durability for security-relevant writes.

## Approved decision

Use PostgreSQL as a transactional audit outbox. Security-relevant writes are not acknowledged unless the audit intent is committed in the same transaction. The outbox dispatcher may be asynchronous, but acceptance into the outbox is not.

## Scope

- Persist domain audit intents transactionally, including writes made by Celery tasks and explicit bulk SQL paths.
- Make write-route audit obligations explicit. Never claim middleware after the business response can roll back a committed write.
- Dispatch with idempotency, bounded retry and backoff, multi-worker safety, observability and a defined shutdown.
- Cover PostgreSQL connection, tenant GUC, insert, commit, crash/restart and concurrent worker failure scenarios with real database tests.

## Non-goals

- Guarantee that an externally committed operation can be rolled back using HTTP middleware after the fact.
- Store secrets, bearer tokens or unsanitized URL paths.
- Use a process-only queue or log output as the durable audit record.
- Make the external monitoring infrastructure part of this repository.

## Related code

`app/adapters/db/domain_audit.py`, `app/adapters/db/session.py`, `app/application/audit_service.py`, `app/adapters/api/middleware/audit.py`, `app/main.py`.

Issue: https://github.com/stritti/nak-district-planner/issues/648
