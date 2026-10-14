# audit-logging Specification

## Purpose

Records security- and governance-relevant actions in `audit_logs`: HTTP-level request audit for state-changing calls and denied access, and transactional domain audit of changes to audited aggregates.

## Requirements

### Requirement: HTTP request audit
`AuditMiddleware` SHALL record state-changing requests (all methods except `GET`, `HEAD`, `OPTIONS`) with action, resource type and ID, actor, client IP, status and outcome, and SHALL record HTTP 403 responses as `ACCESS_DENIED`. Health endpoints SHALL be exempt.

#### Scenario: Forbidden request
- **WHEN** a request is answered with 403
- **THEN** an audit entry with action `ACCESS_DENIED` is written

### Requirement: Transactional domain audit
Inserts, updates and deletes of planning slots, service assignments, calendar integrations and export tokens SHALL be logged in the same transaction (SQLAlchemy `after_flush`) with old and new values of whitelisted fields, including changes made by Celery tasks. A rolled-back transaction SHALL leave no audit entry.

#### Scenario: Rollback
- **WHEN** a transaction modifying a planning slot is rolled back
- **THEN** no audit entry for that modification remains

### Requirement: Secrets are redacted
Credential and token columns SHALL be reported only by name under `changes.redacted_fields`, never with old or new values.

#### Scenario: Credentials rotated
- **WHEN** a calendar integration's credentials change
- **THEN** the audit entry names `credentials_enc` as redacted and contains no value
