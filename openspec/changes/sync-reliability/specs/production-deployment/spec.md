## ADDED Requirements

### Requirement: Reliable Celery transport
The Celery worker and Beat SHALL use the application's Valkey URL as a Redis-protocol broker and result backend, with JSON serialization, late acknowledgements, a 240-second soft task limit and a 300-second hard task limit.

#### Scenario: Deployment uses configured Valkey
- **WHEN** the worker starts with `VALKEY_URL=valkey://valkey:6379/0`
- **THEN** Celery connects to the corresponding `redis://valkey:6379/0` endpoint
- **AND** it does not require SQLAlchemy transport tables
