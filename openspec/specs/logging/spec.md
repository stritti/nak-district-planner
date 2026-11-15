# logging Specification

## Purpose
Strukturiertes, redigiertes und korrelierbares Application-Logging für Backend-API, Celery Worker und Beat sowie das Frontend: JSON Lines auf stdout, konfigurierbarer Level, `request_id`/`task_id` in jeder Zeile. Abgegrenzt vom Audit-Log in der Datenbank (`audit-logging`) und von OpenTelemetry.

## Requirements

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
`LOG_LEVEL` SHALL set the effective root level (default `INFO`); `LOG_LEVEL` and `LOG_FORMAT` SHALL be validated at startup. When `APP_ENV=production` and `LOG_LEVEL=DEBUG`, the service SHALL log one warning and fall back to `INFO`.

#### Scenario: Debug refused in production
- **WHEN** the backend starts with `APP_ENV=production` and `LOG_LEVEL=DEBUG`
- **THEN** a warning is logged once and the effective level is `INFO`

#### Scenario: Per-deployment level
- **WHEN** `LOG_LEVEL=WARNING` is configured
- **THEN** INFO and DEBUG records are not emitted

#### Scenario: Invalid level is rejected at startup
- **WHEN** `LOG_LEVEL` or `LOG_FORMAT` holds a value outside the allowed set
- **THEN** settings validation fails and the service does not start

### Requirement: Secrets and personal data are never logged
The process-wide redaction filter SHALL stay installed on every handler (root, uvicorn and Celery loggers) and both formatters SHALL apply it to the rendered message and stacktrace. Log statements SHALL NOT contain passwords, tokens, credentials, email addresses, personal names, request payloads or URLs with query strings; request paths SHALL be logged only through `redact_secret_path`.

#### Scenario: Export token in an exception message
- **WHEN** an exception message contains an `/api/v1/export/<token>/...` path and is logged
- **THEN** the emitted line contains `{redacted}` instead of the token in message and stacktrace

#### Scenario: Text format is redacted as well
- **WHEN** `LOG_FORMAT=text` is active and a record containing an export token path is logged
- **THEN** the text line contains `{redacted}` instead of the token

#### Scenario: Credential rotation is not logged
- **WHEN** a calendar integration's credentials are updated with a known test secret while log output is captured
- **THEN** the captured output of backend and worker contains no occurrence of the old or new secret

### Requirement: Request correlation ID in every log record
Every log record emitted while handling an HTTP request SHALL carry the request's `request_id`, as determined by the `request-identity` capability, and the request's OTel span SHALL carry it as attribute `request_id`. Records emitted outside a request SHALL NOT carry a stale `request_id` from an earlier request.

#### Scenario: Handler error carries the request ID
- **WHEN** a request handler logs an error
- **THEN** the log line contains the `request_id` of that request

#### Scenario: Span attribute
- **WHEN** a request is traced with OpenTelemetry enabled
- **THEN** the server span carries the same `request_id` as the request's log lines

#### Scenario: No leakage between requests
- **WHEN** a background coroutine logs after its request finished
- **THEN** its record does not carry the `request_id` of a later request

### Requirement: Task correlation ID for background jobs
Celery worker and beat SHALL use the same format and level configuration as the backend API, with `service=worker` respectively `service=beat`, and Celery SHALL NOT replace that configuration with its own root-logger setup. Log records emitted inside a Celery task SHALL carry `task_id` and `task_name`; records after the task SHALL NOT.

#### Scenario: Failing task is correlatable
- **WHEN** a Celery task logs an error
- **THEN** the line is JSON in production and contains `service=worker`, `task_id` and `task_name`

#### Scenario: Beat is distinguishable
- **WHEN** Celery beat logs a scheduling message
- **THEN** the line contains `service=beat` and uses the backend's format

### Requirement: Access log format and health-endpoint exemption
The backend SHALL write one access-log record per HTTP request from its own middleware (the uvicorn access log is disabled) with method, redacted path, status code, duration in milliseconds and `request_id`. Requests to `/health` and `/api/health` and requests rejected by the rate limiter (429) SHALL NOT produce access-log records at `INFO` level.

#### Scenario: Health probe stays quiet
- **WHEN** `/api/health` is polled every 30 seconds
- **THEN** no access-log line is emitted at `INFO`

#### Scenario: Access line carries no secret path
- **WHEN** the ICS export feed is requested
- **THEN** the access-log line contains the redacted path, not the bearer token

#### Scenario: Access line carries duration
- **WHEN** a request to `/api/v1/events` completes
- **THEN** exactly one access-log line with method, redacted path, status, `duration_ms` and `request_id` is emitted

#### Scenario: Rate-limited flood stays quiet
- **WHEN** a client receives 429 responses from the rate limiter
- **THEN** those requests produce no access-log line at `INFO`

### Requirement: Application logs go to stdout only
The application SHALL NOT write log files itself; stdout/stderr SHALL be the only sink, with rotation and retention handled by the container runtime. Log output SHALL be retrievable redacted via `nakctl logs analyze` / `nakctl logs export`.

#### Scenario: No log files in the container
- **WHEN** the backend writes logs during normal operation
- **THEN** no log files are created inside the container filesystem

### Requirement: Frontend logging rules
The frontend SHALL log through a central logger utility: in development `debug`/`info` may write to the console; in production only `warn`/`error` emit. The logger SHALL replace values of keys matching `token`, `password`, `secret`, `credential`, `email` or `name` (case-insensitive, nested) with `[redacted]`, SHALL NOT log request or response payloads, and the frontend SHALL NOT send browser logs to the server.

#### Scenario: Production build stays silent on debug
- **WHEN** a production build executes a `debug` log call with a user object
- **THEN** nothing is written to the console and nothing is sent to the server

#### Scenario: Sensitive fields are masked
- **WHEN** `logger.error` is called with an object containing `email` and a nested `accessToken`
- **THEN** both values appear as `[redacted]` in the console output
