# csrf-protection Specification

## Purpose

Protects state-changing browser requests, including the cookie-backed OIDC token, refresh and revoke calls, with HMAC-signed, rotating CSRF tokens.

## Requirements

### Requirement: Signed CSRF token on state-changing requests
`CSRFMiddleware` SHALL require a valid HMAC-signed token for every request whose method is not `GET`, `HEAD` or `OPTIONS`, except the health endpoints and `/api/v1/auth/oidc/discovery`, and SHALL respond with 403 `CSRF validation failed` otherwise. The token is read from the `X-CSRF-Token` header, falling back to the `csrf_token` cookie (header-only enforcement is tracked separately). There SHALL be no header-based exemption.

#### Scenario: Missing token
- **WHEN** a `POST` without CSRF header or cookie reaches a protected path
- **THEN** the API responds with 403

### Requirement: Token issuance and rotation
Every response passing the middleware SHALL set a fresh `csrf_token` cookie readable by JavaScript so the SPA can send it in the request header; the SPA SHALL read the current cookie at request time.

#### Scenario: Token rotates after a write
- **WHEN** a valid state-changing request completes
- **THEN** the response carries a new CSRF cookie
