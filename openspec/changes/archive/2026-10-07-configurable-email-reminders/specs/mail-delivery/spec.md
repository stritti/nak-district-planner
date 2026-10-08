## ADDED Requirements

### Requirement: MailService SHALL provide an abstract port
The system SHALL define an abstract MailService port that all mail adapters implement.

#### Scenario: Port definition
- **WHEN** the system loads
- **THEN** the MailService ABC SHALL define a `send(to: list[str], subject: str, body: str)` method that raises NotImplementedError

### Requirement: SMTP adapter SHALL send emails via SMTP server
The system SHALL provide an SMTP mail adapter that connects to a configurable SMTP server for production use.

#### Scenario: Successful send via SMTP
- **WHEN** the SMTP adapter is called with a valid recipient list, subject, and body
- **THEN** the adapter SHALL connect to the configured SMTP server and deliver the message

#### Scenario: SMTP connection failure
- **WHEN** the SMTP adapter cannot connect to the SMTP server
- **THEN** the adapter SHALL raise a MailDeliveryError

#### Scenario: Configuration from environment
- **WHEN** the system starts
- **THEN** the SMTP adapter SHALL read SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD, and EMAIL_FROM_ADDRESS from environment variables

### Requirement: Log adapter SHALL write emails to application log
The system SHALL provide a log mail adapter that writes email details to the application logger for development use.

#### Scenario: Log send
- **WHEN** the log adapter is called with recipient list, subject, and body
- **THEN** the adapter SHALL log the email content at INFO level

### Requirement: Mock adapter SHALL capture emails in memory
The system SHALL provide a mock mail adapter that stores sent emails in an in-memory list for testing.

#### Scenario: Capture sent emails
- **WHEN** the mock adapter is called with recipient list, subject, and body
- **THEN** the adapter SHALL append a MailRecord (to, subject, body) to an internal list

#### Scenario: Retrieve captured emails
- **WHEN** a test inspects the mock adapter's sent list
- **THEN** the adapter SHALL return all captured MailRecord instances

#### Scenario: Clear captured emails
- **WHEN** a test calls clear() on the mock adapter
- **THEN** the adapter SHALL empty its internal sent list

### Requirement: System footer SHALL be appended to all emails
The system SHALL append a configurable footer to every outgoing email body.

#### Scenario: Footer appended
- **WHEN** any mail adapter sends an email with a body
- **THEN** the system SHALL append the EMAIL_FOOTER text (separated by `\n---\n`) before passing the body to the adapter

#### Scenario: Empty footer
- **WHEN** EMAIL_FOOTER is not configured or empty
- **THEN** the system SHALL NOT append any separator or footer text to the body
