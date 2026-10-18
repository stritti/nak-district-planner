## ADDED Requirements

### Requirement: External ingress does not log ICS bearer credentials
The deployed public ingress SHALL avoid storing the raw bearer token from `/api/v1/export/<token>/calendar.ics` in any access log, structured event, span attribute or downstream observability pipeline.

#### Scenario: Proxy access log
- **WHEN** a client requests a bearer-token ICS feed through the external TLS proxy
- **THEN** the external access log contains no raw token value
- **AND** disabling logs for that route is acceptable when reliable redaction is unavailable

#### Scenario: Telemetry transport
- **WHEN** the request is traced or sent to central monitoring
- **THEN** no URL path attribute exposes the bearer token

### Requirement: Historic exposure is remediated
The operator SHALL inspect retained proxy and telemetry logs for potentially exposed valid bearer tokens, restrict/expire retention as appropriate and revoke/reissue affected feed credentials.

#### Scenario: Token appears in old logs
- **WHEN** a still-valid bearer token is detected in accessible historical logs
- **THEN** the subscription is revoked and a replacement is issued through the approved rotation procedure

### Requirement: Canary verification is an external release gate
A non-disclosing canary check SHALL exercise the actual public TLS ingress and every relevant logging sink. Its result SHALL be documented in the production runbook and SHALL NOT contain a credential.

#### Scenario: Incomplete evidence
- **WHEN** a proxy, telemetry sink or historic log store cannot be inspected
- **THEN** the operational acceptance is not marked complete and the issue remains open
