## ADDED Requirements

### Requirement: Reliable Celery transport
The Celery worker and Beat SHALL use the application's Valkey URL as a Redis-protocol broker and result backend, with JSON serialization and a prefetch multiplier of one. Only the retry-safe calendar sync task SHALL use late acknowledgements and a 240-second soft / 300-second hard time limit; non-idempotent mail and maintenance jobs SHALL not inherit these settings.

#### Scenario: Deployment uses configured Valkey
- **WHEN** the worker starts with `VALKEY_URL=valkey://valkey:6379/0`
- **THEN** Celery connects to the corresponding `redis://valkey:6379/0` endpoint
- **AND** it does not require SQLAlchemy transport tables
