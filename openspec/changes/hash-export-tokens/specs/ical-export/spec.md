## MODIFIED Requirements

### Requirement: Export token management

`POST`, `GET` and `DELETE /api/v1/export-tokens` SHALL require `DISTRICT_ADMIN` of the token's district (listing without `district_id` only for superadmins), except for existing subject-bound personal token operations: a verified owner MAY create or list their own district-scoped INTERNAL token within their current effective scope and MAY revoke their own token after membership loss. Tokens SHALL be generated with `secrets.token_urlsafe(32)`, typed `PUBLIC` or `INTERNAL`, and MAY be scoped to a congregation or a leader. During this expand phase, new token rows SHALL additionally store a SHA-256 hash of the secret in nullable `token_hash`, while retaining the original plaintext for rollback compatibility. The plaintext secret SHALL be returned only in the creation response and SHALL NOT be included in listings.

#### Scenario: Token created

- **WHEN** an authorized caller creates an export token
- **THEN** the creation response contains the plaintext secret
- **AND** the stored row contains the unchanged secret and its SHA-256 hash

#### Scenario: Token listed

- **WHEN** export tokens are listed
- **THEN** responses contain metadata and `token: null`, with no reusable secret or digest

#### Scenario: Legacy rows backfilled

- **WHEN** the expand migration runs on existing plaintext tokens
- **THEN** each existing token receives its SHA-256 digest without changing the original secret
- **AND** a secret that looks like a 64-character hexadecimal digest is still backfilled as plaintext

#### Scenario: Rollback-compatible old writer

- **WHEN** a previous application release reads or creates tokens against the expanded schema
- **THEN** the plaintext contract continues to work even when `token_hash` is null

#### Scenario: Token deleted

- **WHEN** a token is deleted
- **THEN** subsequent feed requests with it respond with 404

### Requirement: ICS feed endpoint

`GET /api/v1/export/{token}/calendar.ics` SHALL be unauthenticated, respond with 404 for unknown tokens, set the presented plaintext token as RLS context, resolve the token using the existing plaintext lookup, and return `text/calendar` covering planning slots from one year back to two years ahead (narrowed to the congregation for congregation tokens). The `approval_status` query parameter SHALL accept `confirmed_only` or `include_planned`. Hash-only lookup and hash-aware RLS authorization are outside this expand phase.

#### Scenario: Unknown token

- **WHEN** the feed is requested with an unknown token or a stored digest instead of its original secret
- **THEN** the endpoint responds with 404 without revealing token metadata

#### Scenario: Existing subscription after expansion

- **WHEN** a calendar uses its original subscription URL after migration
- **THEN** its authorization scope and feed content remain unchanged

#### Scenario: Invitation copy location

- **WHEN** a slot is an invitation copy of another congregation's service
- **THEN** its `LOCATION` is the host congregation, not the invited one, and the host's Dienstleiter appears in the `COMMENT` (anonymised in public feeds)

#### Scenario: Default approval filter

- **WHEN** a public token without leader scope is used without `approval_status`
- **THEN** only `CONFIRMED` slots are exported; other tokens also export `PLANNED` slots marked `STATUS:TENTATIVE`

## ADDED Requirements

### Requirement: One-time calendar link remains usable in the current scope

The frontend SHALL immediately expose a complete, copyable subscription URL after creation, SHALL preserve it across event-date reloads and failures of ancillary display-name requests, and SHALL clear secrets held in memory when the identity or district changes. Secrets SHALL NOT be persisted in browser storage.

#### Scenario: Copy into an external calendar

- **WHEN** the owner copies a newly created personal calendar link
- **THEN** the copied URL includes the application origin and the encoded token path

#### Scenario: Date range changed

- **WHEN** the owner changes the event date range during or after token creation
- **THEN** event loading does not discard the token's one-time URL, even when that loading fails

#### Scenario: Congregation names unavailable

- **WHEN** token creation succeeds and congregation-name loading is pending or fails
- **THEN** the creation dialog closes and the created link remains copyable
- **AND** an ancillary name-loading error does not report token creation as failed

#### Scenario: Identity or district changed

- **WHEN** the current identity or district changes
- **THEN** previous secrets are cleared immediately and delayed responses for the previous scope are ignored
