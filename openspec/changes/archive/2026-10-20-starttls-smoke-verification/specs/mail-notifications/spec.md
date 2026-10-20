## ADDED Requirements

### Requirement: STARTTLS must be verified against a real SMTP server
The SMTP adapter SHALL be integration-tested with a local TLS-capable SMTP test server and SHALL NOT authenticate until STARTTLS has succeeded with a certificate- and hostname-validating SSL context.

#### Scenario: Valid STARTTLS
- **WHEN** a trusted local SMTP server advertises STARTTLS with a matching hostname
- **THEN** the client negotiates TLS before sending authentication credentials
- **AND** a test message is accepted by the local server only after the expected handshake

#### Scenario: No STARTTLS advertised
- **WHEN** an authenticated SMTP connection encounters a server without STARTTLS
- **THEN** the send attempt fails and no AUTH command is sent

#### Scenario: Invalid certificate or hostname
- **WHEN** the server's certificate is untrusted or its hostname does not match
- **THEN** the send attempt fails without sending AUTH or message data

#### Scenario: STARTTLS handshake failure
- **WHEN** an advertised STARTTLS handshake fails
- **THEN** no authentication or message content is sent

### Requirement: Staging relay smoke validation
An operator SHALL verify the configured staging/production relay hostname and STARTTLS certificate before enabling credentialed SMTP delivery. This operation SHALL not log passwords or send external mail in handshake-only mode.

#### Scenario: Predeployment verification
- **WHEN** the operator runs the relay smoke check
- **THEN** TLS verification and the recorded result are available in the production runbook
