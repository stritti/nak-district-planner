## ADDED Requirements

### Requirement: Durable synchronization failure state
A failed calendar synchronization SHALL preserve the previous successful synchronization timestamp and SHALL store a sanitized error and the time of the most recent attempt in a separate committed transaction.

#### Scenario: Provider failure causes rollback
- **WHEN** importing an integration raises an exception
- **THEN** event mutations are rolled back
- **AND** a distinct transaction persists the attempt timestamp and a sanitized failure class
- **AND** the last successful synchronization timestamp is not advanced

### Requirement: Non-blocking integration synchronization
A sync attempt SHALL use a transaction-scoped PostgreSQL try-advisory lock keyed to integration ID.

#### Scenario: Concurrent task owns lock
- **WHEN** the lock cannot be acquired
- **THEN** the second invocation returns a skipped result and logs the reason without fetching provider events

### Requirement: Bounded task scheduling
Periodic dispatch SHALL consider both the previous success and latest attempt, avoiding duplicate retry chains for integrations in backoff.

#### Scenario: Failed attempt waiting for retry
- **WHEN** the latest attempt is less than 30 minutes ago
- **THEN** Beat does not dispatch another sync for that integration
