# Tasks

- [x] Persist last_attempt_at in domain, ORM, API response, repository and migration.
- [x] Commit sanitized task errors outside failed event transaction.
- [x] Skip locked integration via try-advisory lock.
- [x] Suppress redispatch during backoff; mark scheduled dispatches.
- [x] Configure Valkey for Celery with soft/hard limits and late ack.
- [x] Run backend unit/integration tests, migration graph, Docker image validation, security scans and coverage gate in CI. (Documentation CI is independently blocked by unrelated OpenSpec changes.)
