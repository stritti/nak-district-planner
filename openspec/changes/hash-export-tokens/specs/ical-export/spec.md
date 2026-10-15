## MODIFIED Requirements

### Requirement: Export token management

`POST`, `GET` and `DELETE /api/v1/export-tokens` SHALL require `DISTRICT_ADMIN` of the token's district (listing without `district_id` only for superadmins). Tokens SHALL be generated with `secrets.token_urlsafe(32)`, typed `PUBLIC` or `INTERNAL`, and MAY be scoped to a congregation or a leader. Only a SHA-256 hash of the token SHALL be persisted; the plaintext secret SHALL be returned exactly once in the creation response. Listing SHALL return token metadata without a reusable secret. A `POST /api/v1/export-tokens/{id}/reveal` endpoint SHALL return the plaintext secret of a not-yet-hashed legacy token exactly once and hash it thereafter; it SHALL require the same role as deletion and respond 404 for already-hashed tokens.

#### Scenario: Token created

- **WHEN** a district admin creates an export token
- **THEN** the response contains the plaintext secret exactly once
- **AND** only its SHA-256 hash is stored

#### Scenario: Token listed

- **WHEN** export tokens are listed
- **THEN** the response contains metadata only and no reusable secret

#### Scenario: Legacy token revealed once

- **WHEN** a district admin reveals a legacy plaintext token
- **THEN** the plaintext secret is returned exactly once and the stored value is replaced by its hash
- **AND** a second reveal responds with 404

#### Scenario: Token deleted

- **WHEN** a token is deleted
- **THEN** subsequent feed requests with it respond with 404

### Requirement: ICS feed endpoint

`GET /api/v1/export/{token}/calendar.ics` SHALL be unauthenticated, respond with 404 for unknown tokens, hash the presented token for lookup and RLS context, and return `text/calendar` covering planning slots from one year back to two years ahead (narrowed to the congregation for congregation tokens). The `approval_status` query parameter SHALL accept `confirmed_only` or `include_planned`.

#### Scenario: Unknown token

- **WHEN** the feed is requested with an unknown token
- **THEN** the endpoint responds with 404 without revealing whether a token exists

#### Scenario: Invitation copy location

- **WHEN** a slot is an invitation copy of another congregation's service
- **THEN** its `LOCATION` is the host congregation, not the invited one, and the host's Dienstleiter appears in the `COMMENT` (anonymised in public feeds)

#### Scenario: Default approval filter

- **WHEN** a public token without leader scope is used without `approval_status`
- **THEN** only `CONFIRMED` slots are exported; other tokens also export `PLANNED` slots marked `STATUS:TENTATIVE`
