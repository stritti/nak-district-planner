## Why

Issue #648: the HTTP audit writer in `AuditService._writer` takes an entry from a process-local queue, loses it after a failed PostgreSQL write and acknowledges it anyway; a crash drops everything queued. Reviewing the code for this change showed two more facts that shape the fix:

- Domain audit (`domain_audit`, `after_flush`) already writes into `audit_logs` in the same transaction as the change. It cannot be lost; only the HTTP-level audit can.
- The request transaction is committed by the `get_db_session` dependency's exit code, which FastAPI (0.143, default dependency scope) runs **after** the response was produced. A failed commit still reaches the client as a success while the change and its domain audit roll back.

## Decision

No outbox. An outbox lives in the same database as `audit_logs`, so it is no more durable than a direct insert. Instead:

1. Commit before the response, so that a failed commit becomes an error response.
2. Write the HTTP audit synchronously: inside the request transaction for successful writes that no domain audit covers, in its own short transaction before the response for failures and denials. If it cannot be persisted, the API answers with a service error instead of an unaudited result.
3. Remove the in-memory queue and its writer.

## Scope

- `app/adapters/db/session.py` (`get_db_session`, dependency scope), `app/adapters/api/deps.py`, `app/adapters/api/middleware/audit.py`, `app/application/audit_service.py`, `app/main.py`.
- Metrics and runbook for audit persistence failures.

## Non-goals

- A new table, migration, dispatcher, retry queue or quarantine.
- Auditing successful reads.
- Making an already committed change fail afterwards.
- Storing secrets, bearer tokens or unredacted URL paths.

Issue: https://github.com/stritti/nak-district-planner/issues/648
