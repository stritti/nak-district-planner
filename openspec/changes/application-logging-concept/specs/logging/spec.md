## ADDED Requirements

### Requirement: Structured JSON log format in production
The backend API, Celery worker and Celery beat SHALL emit one JSON object per log line on stdout when `LOG_FORMAT=json` (the default when `APP_ENV` is not `development`). Each line SHALL contain `timestamp` (UTC, ISO 8601), `level`, `logger`, `message`, `service` (`backend`, `worker` or `beat`), `env` and `version`; error records SHALL additionally contain an `exception` object with type, message and stacktrace.

#### Scenario: Production log line
- **WHEN** the backend logs an INFO message with `APP_ENV=production`
- **THEN** stdout receives a single JSON line with the mandatory fields above

#### Scenario: Development stays readable
- **WHEN** `APP_ENV=development` and `LOG_FORMAT` is unset
- **THEN** logs use the human-readable text format instead of JSON

#### Scenario: Explicit format override
- **WHEN** `LOG_FORMAT=text` is set in production
- **THEN** logs use the text format despite `APP_ENV=production`

### Requirement: Configurable log level with production guard
`LOG_LEVEL` SHALL set the effective root level (default `INFO`). When `APP_ENV=production` and `LOG_LEVEL=DEBUG`, the service SHALL log one warning and fall back to `INFO`.

#### Scenario: Debug refused in production
- **WHEN** the backend starts with `APP_ENV=production` and `LOG_LEVEL=DEBUG`
- **THEN** a warning is logged once and the effective level is `INFO`

#### Scenario: Per-deployment level
- **WHEN** `LOG_LEVEL=WARNING` is configured
- **THEN** INFO and DEBUG records are not emitted

### Requirement: Secrets and personal data are never logged
The process-wide redaction filter SHALL stay installed on every handler (root and uvicorn loggers) and SHALL also be applied by the JSON formatter to the rendered message and stacktrace. Log statements SHALL NOT contain passwords, tokens, credentials, email addresses, personal names, request payloads or URLs with query strings; request paths SHALL be logged only through `redact_secret_path`.

#### Scenario: Export token in an exception message
- **WHEN** an exception message contains an `/api/v1/export/<token>/...` path and is logged
- **THEN** the emitted line contains `{redacted}` instead of the token in message and stacktrace

#### Scenario: Credential rotation is not logged
- **WHEN** a calendar integration's credentials change
- **THEN** no application log line contains the old or new credential value

### Requirement: Request correlation ID in every log record
Each HTTP request SHALL receive exactly one `request_id`: the `X-Request-ID` header is honored only when the TCP peer lies in `TRUSTED_PROXIES` (same rule as the client IP in the `request-identity` spec), otherwise a UUID is generated. Every log record emitted while handling that request SHALL carry the `request_id`, the audit entry in `audit_logs` SHALL store the same `request_id`, and the OTel span SHALL carry it as an attribute.

#### Scenario: Log line correlated with audit entry
- **WHEN** a state-changing request is audited and its handler logs an error
- **THEN** both the log line and the `audit_logs` row contain the identical `request_id`

#### Scenario: Client-supplied ID from an untrusted peer
- **WHEN** a peer outside `TRUSTED_PROXIES` sends `X-Request-ID`
- **THEN** a fresh UUID is used instead of the header value

#### Scenario: Client-supplied ID from a trusted proxy
- **WHEN** the frontend nginx forwards a request with a valid `X-Request-ID`
- **THEN** that ID is used in the logs and the audit entry

### Requirement: Task correlation ID for background jobs
Log records emitted inside a Celery task SHALL carry `task_id` and `task_name`; worker and beat SHALL use the same format and level configuration as the backend API.

#### Scenario: Failing task is correlatable
- **WHEN** a Celery task logs an error
- **THEN** the line is JSON in production and contains `service=worker`, `task_id` and `task_name`

### Requirement: Access log format and health-endpoint exemption
The uvicorn access log SHALL use a defined format with method, redacted path, status code and duration. Requests to `/health` and `/api/health` SHALL NOT produce access-log lines at `INFO` level.

#### Scenario: Health probe stays quiet
- **WHEN** `/api/health` is polled every 30 seconds
- **THEN** no access-log line is emitted at `INFO`

#### Scenario: Access line carries no secret path
- **WHEN** the ICS export feed is requested
- **THEN** the access-log line contains the redacted path, not the bearer token

### Requirement: Application logs go to stdout only
The application SHALL NOT write log files itself; stdout/stderr SHALL be the only sink, with rotation and retention handled by the container runtime. Log output SHALL be retrievable redacted via `nakctl logs analyze` / `nakctl logs export`.

#### Scenario: No log files in the container
- **WHEN** the backend writes logs during normal operation
- **THEN** no log files are created inside the container filesystem

### Requirement: Frontend logging rules
The frontend SHALL log through a central logger utility: in development `debug`/`info` may write to the console; in production only `warn`/`error` emit. The logger SHALL drop fields named `token`, `password` or `email` and SHALL NOT log request payloads, and the frontend SHALL NOT send browser logs to the server.

#### Scenario: Production build stays silent on debug
- **WHEN** a production build executes a `debug` log call with a user object
- **THEN** nothing is written to the console and nothing is sent to the server
