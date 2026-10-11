## ADDED Requirements

### Requirement: Reliable Celery transport
The Celery worker and Beat SHALL use the application's Valkey URL as a Redis-protocol broker and result backend, with JSON serialization and a prefetch multiplier of one. Only the retry-safe calendar sync task SHALL use late acknowledgements and a 240-second soft / 300-second hard time limit; non-idempotent mail and maintenance jobs SHALL not inherit these settings.

#### Scenario: Deployment uses configured Valkey
- **WHEN** the worker starts with `VALKEY_URL=valkey://valkey:6379/0`
- **THEN** Celery connects to the corresponding `redis://valkey:6379/0` endpoint
- **AND** it does not require SQLAlchemy transport tables

### Requirement: Lossless SQL-to-Valkey broker cutover
When upgrading from the SQLAlchemy transport to Valkey, workers and Beat SHALL refuse startup if the legacy SQL Kombu queue retains any messages. Deployment SHALL require stopping old Beat, draining and verifying the old worker queue, and only then switching broker transports. Non-idempotent mail tasks SHALL NOT be blindly replayed.

#### Scenario: Legacy SQL messages remain
- **GIVEN** the existing SQL broker contains queued or reserved messages
- **WHEN** new Valkey workers or Beat start
- **THEN** startup fails with remediation instructions before consuming new jobs

#### Scenario: Drained broker
- **GIVEN** the legacy SQL broker has no remaining messages
- **WHEN** new workers start with Valkey configured
- **THEN** startup proceeds and the old tables remain intact
