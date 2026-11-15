## ADDED Requirements

### Requirement: Audit entries share the request correlation ID
An audit entry written for or during an HTTP request SHALL store the request's `request_id` as determined by the `request-identity` capability, so that `audit_logs.request_id` matches the application log records of the same request. The audit middleware SHALL NOT generate a separate ID.

#### Scenario: Log line correlated with audit entry
- **WHEN** a state-changing request is audited and its handler logs an error
- **THEN** both the log line and the `audit_logs` row contain the identical `request_id`

#### Scenario: Denied request
- **WHEN** a request is answered with 403
- **THEN** the `ACCESS_DENIED` audit entry carries the same `request_id` as the request's access-log line
