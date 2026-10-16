## MODIFIED Requirements

### Requirement: Export token management

`POST`, `GET` and `DELETE /api/v1/export-tokens` SHALL require `DISTRICT_ADMIN` of the token's district (listing without `district_id` only for superadmins). Tokens SHALL be generated with `secrets.token_urlsafe(32)`, typed `PUBLIC` or `INTERNAL`, and MAY be scoped to a congregation or a leader. Each token row SHALL additionally store a SHA-256 hash of the secret in `token_hash`; the plaintext secret SHALL be returned exactly once in the creation response and SHALL NOT be included in listings.

#### Scenario: Token created

- **WHEN** a district admin creates an export token
- **THEN** the response contains the plaintext secret exactly once
- **AND** the stored row carries the secret's SHA-256 hash in `token_hash`

#### Scenario: Token listed

- **WHEN** export tokens are listed
- **THEN** the response contains metadata only and no reusable secret

#### Scenario: Token deleted

- **WHEN** a token is deleted
- **THEN** subsequent feed requests with it respond with 404

### Requirement: ICS feed endpoint

`GET /api/v1/export/{token}/calendar.ics` SHALL be unauthenticated, respond with 404 for unknown tokens, set the presented token as RLS context, look the row up by the presented value with a fallback to the hashed column, and return `text/calendar` covering planning slots from one year back to two years ahead (narrowed to the congregation for congregation tokens). The `approval_status` query parameter SHALL accept `confirmed_only` or `include_planned`.

#### Scenario: Unknown token

- **WHEN** the feed is requested with an unknown token
- **THEN** the endpoint responds with 404 without revealing whether a token exists

#### Scenario: Invitation copy location

- **WHEN** a slot is an invitation copy of another congregation's service
- **THEN** its `LOCATION` is the host congregation, not the invited one, and the host's Dienstleiter appears in the `COMMENT` (anonymised in public feeds)

#### Scenario: Default approval filter

- **WHEN** a public token without leader scope is used without `approval_status`
- **THEN** only `CONFIRMED` slots are exported; other tokens also export `PLANNED` slots marked `STATUS:TENTATIVE`
