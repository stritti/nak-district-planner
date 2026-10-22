## MODIFIED Requirements

### Requirement: HTTP request audit
Every denied request (403, any method) and every failed state-changing request SHALL be recorded synchronously before the response is returned; if the entry cannot be persisted the API SHALL answer with 503 instead of the unaudited response. A successful state-changing request SHALL be recorded in the request transaction unless a domain audit entry for it exists. Health endpoints SHALL be exempt.

#### Scenario: Forbidden request
- **WHEN** a request is answered with 403
- **THEN** an audit entry with action `ACCESS_DENIED` is written before the response is returned

#### Scenario: Audit entry cannot be written for a denial
- **WHEN** the database rejects the audit insert of a denied request
- **THEN** the API answers with 503 and the failure is counted, and the 403 is not returned as audited

#### Scenario: Write without a domain audit entry
- **WHEN** a state-changing request succeeds on a resource that has no domain audit
- **THEN** its HTTP audit entry commits in the same transaction as the change

#### Scenario: Write with a domain audit entry
- **WHEN** a state-changing request succeeds and its changes produced domain audit entries
- **THEN** no additional HTTP audit entry is written for it

## ADDED Requirements

### Requirement: Writes are acknowledged only after the commit
The request transaction SHALL be committed before the response is sent. A failed commit SHALL produce an error response and leave neither the change nor its audit entries.

#### Scenario: Commit fails
- **WHEN** PostgreSQL rejects the commit of a state-changing request
- **THEN** the client receives a 5xx response and no audit entry or change remains

### Requirement: Audit failures are observable
The service SHALL count audit persistence failures and log them without request payloads or secrets.

#### Scenario: Persistence failure logged
- **WHEN** an audit entry cannot be persisted
- **THEN** a failure counter increases and the log line contains no payload data
