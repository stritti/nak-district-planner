## MODIFIED Requirements

### Requirement: Durable audit acceptance for security-relevant writes
The system SHALL persist an audit intent in PostgreSQL in the same transaction as each security-relevant business change. If durable acceptance fails, the business transaction SHALL roll back and SHALL NOT return a successful write result. Every state-changing path SHALL have a documented transactional or pre-side-effect audit boundary.

#### Scenario: Audit outbox insert or commit fails
- **WHEN** PostgreSQL rejects the outbox insert, tenant-context setup, or transaction commit
- **THEN** the audited business mutation is not committed
- **AND** the caller receives an error instead of success

#### Scenario: Bulk writes bypass ORM hooks
- **WHEN** a bulk SQL mutation affects an audited resource
- **THEN** its outbox event is persisted in the same transaction without relying on ORM after_flush

#### Scenario: Missing tenant metadata
- **WHEN** an audited write cannot determine the tenant required by row-level security
- **THEN** the write fails closed instead of skipping the audit

### Requirement: At-least-once dispatch without duplicate audit rows
The dispatcher SHALL preserve accepted events across crashes and temporary PostgreSQL failures; it SHALL insert no more than one final audit row per stable event ID. It SHALL use bounded database batches, controlled concurrency, capped backoff and explicit quarantine for poison events.

#### Scenario: Dispatcher fails between final insert and acknowledgement
- **WHEN** a dispatcher retries an already written outbox event
- **THEN** the audit row is not duplicated and the outbox event can be acknowledged safely

#### Scenario: Database unavailable during delivery
- **WHEN** a worker cannot open a session, set worker context, or commit delivery
- **THEN** the durable event remains recoverable, no event is silently discarded
- **AND** the retry is bounded and an observable failure signal is produced

#### Scenario: Crash and restart
- **WHEN** a process is terminated without graceful shutdown
- **THEN** an already committed outbox event is deliverable after restart

### Requirement: Safe shutdown and operational alerts
The system SHALL stop claiming new events on shutdown, drain the active batch for at most 10 seconds and leave unfinished events durable. Monitoring SHALL report backlog count, oldest pending age, retry rate and quarantined records.

#### Scenario: Sustained outage
- **WHEN** PostgreSQL stays unavailable
- **THEN** the process SHALL avoid an unbounded in-memory backlog
- **AND** security-relevant writes SHALL fail closed, with alertable metrics

### Requirement: Denied request audit survives persistence failures
The HTTP audit path for rejected actions SHALL durably record the event before final response where no business transaction exists. Failure to persist SHALL produce a safe service error and a visible operational signal.

#### Scenario: Access denied while database unavailable
- **WHEN** a denied request cannot persist its audit event
- **THEN** the service SHALL NOT claim a fully audited denial response
