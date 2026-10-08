# rate-limiting Specification

## Purpose

Protects the API against abuse with a Valkey-backed sliding-window rate limiter applied as middleware.

## Requirements

### Requirement: Sliding-window limits
`RateLimitMiddleware` SHALL limit requests per identifier (`user:{sub}` for authenticated, otherwise `ip:{address}`) with a default of 200 requests per 60 s (doubled for authenticated users), a burst limit of 10 per second, and stricter per-endpoint limits for OIDC discovery/token, export feeds, events and health. Exceeded limits SHALL respond with HTTP 429. `/health`, `/api/health` and `OPTIONS` SHALL be exempt.

#### Scenario: Burst exceeded
- **WHEN** a client sends more than 10 requests within one second
- **THEN** further requests in that second receive 429

### Requirement: Observable fail-open
If Valkey is unavailable the limiter SHALL fail open, log the condition and increment a fail-open metric with the cause.

#### Scenario: Valkey down
- **WHEN** the limiter cannot reach Valkey
- **THEN** requests are served and the fail-open counter increases
