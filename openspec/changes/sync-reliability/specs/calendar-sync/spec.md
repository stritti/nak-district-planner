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
Periodic dispatch SHALL consider both the previous success and latest attempt, avoiding duplicate retry chains for integrations in backoff. A scheduled attempt SHALL be stamped only after the broker accepts that specific task; failed dispatch SHALL remain eligible for the next scheduling cycle. Timestamp updates SHALL NOT overwrite concurrent integration configuration or success/error status. After a failed attempt, the effective retry cooldown SHALL be at least 30 minutes, even if the configured `sync_interval` is shorter.

#### Scenario: Failed attempt waiting for retry
- **WHEN** the latest attempt is less than 30 minutes ago
- **THEN** Beat does not dispatch another sync for that integration

#### Scenario: Broker dispatch fails
- **WHEN** Valkey rejects a scheduled sync task
- **THEN** the integration remains due for a future Beat cycle and its last attempt is not advanced

#### Scenario: Integration edited while scheduling
- **WHEN** a user modifies integration configuration during scheduling
- **THEN** scheduling does not overwrite those changes or successful sync status

#### Scenario: Fast worker completes before dispatch timestamp is committed
- **WHEN** a sync task completes between successful broker publish and scheduler timestamp commit
- **THEN** the stored scheduled timestamp does not exceed the publish time and the successful sync is not misclassified as a pending attempt

#### Scenario: Worker process exits abruptly
- **WHEN** the worker process exits after accepting a sync task but before completion
- **THEN** the broker requeues the late-acknowledged sync task rather than silently dropping it
