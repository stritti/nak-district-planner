# Durable HTTP Audit Design

## Baseline

* `AuditedSession` inserts domain audit rows in `after_flush` on the flushing connection: entry and change commit or roll back together. A mutation whose tenant cannot be resolved is rejected (`AuditTenantResolutionError`, first slice of this change).
* `AuditMiddleware` records state-changing requests (not `GET`/`HEAD`/`OPTIONS`) and every 403 after `call_next`, through `AuditService.log`, which puts the entry on an unbounded `asyncio.Queue`; `_writer` writes it in its own session, logs and drops it on any error.
* `get_db_session` yields a session and commits after the `yield`. With FastAPI's default dependency scope the exit code runs after the response object exists (verified: handler, middleware sees 200, commit fails, client receives 200).

## Decisions

### 1. The commit happens before the response

Declare the session dependency with `scope="function"`. Its exit code, including `commit()`, then runs when the route function returns, before the response is sent; a failed commit becomes a 500. FastAPI accepts a request-scoped dependency (`get_current_user`) that depends on it. The repository's session consumers are few (`deps.py`), so the change is one constant. This is the acceptance boundary for every audited write.

### 2. Failures and denials: synchronous durable insert

For a 403 (any method) and for failed state-changing requests (4xx/5xx or exception) there is no business transaction to join. The middleware inserts the entry in its own short transaction with the system-worker context **before** returning the response. If the insert fails, the response is replaced by `503` with a fixed body; the failure is counted (`audit_write_failures_total`) and logged without payload. Exempt paths (health) stay exempt.

### 3. Successful writes: no second entry, no extra failure mode

A request marks, in a request-scoped context variable, when the session wrote a domain audit row. For a successful state-changing request:

* with a domain audit row: no HTTP entry (no duplicate);
* without one (routes on aggregates the domain audit does not cover): the session dependency inserts the HTTP entry into the **same transaction** just before the commit, so it exists exactly when the change does.

The in-transaction entry cannot know the final status code of the response; it records outcome `SUCCESS` and the method, path and request id.

### 4. Remove the queue

`AuditService` loses `_queue`, `_writer`, `start` and `stop`; the lifespan hooks that start it disappear. What remains is the building of `AuditLogCreate` and a synchronous `record(...)` used by the middleware and the session dependency.

### 5. Verification

Real-PostgreSQL tests with real fault injection: failing commit gives 500 and leaves neither change nor audit row; failing audit insert on a denial gives 503; a write without domain audit commits its HTTP row atomically; a write with domain audit has exactly one entry; a rolled-back failed request still produces a `FAILED` entry. Unit tests for the context marker and the 503 path. Backend coverage stays at or above 80 %.

## Alternatives rejected

* PostgreSQL outbox with dispatcher: same database, no gain in durability, large new surface (table, RLS, worker role, backoff, quarantine).
* Retry queue in memory: lost on crash and under sustained failure.
* Auditing in the middleware after the commit: cannot make a committed change fail.

## Risks

* A database outage now turns 403 into 503 for denied requests and blocks writes; that matches the intent (no unaudited results), and the database is already required for authentication.
* Each denial costs one insert on the request path (previously asynchronous). Denial floods are already limited by the rate limiter in front of the routes.
* Function-scoped session exit means the session is closed before response serialisation; routes must not lazy-load after returning (`expire_on_commit=False` and eager loading already hold, and are covered by the suite).
