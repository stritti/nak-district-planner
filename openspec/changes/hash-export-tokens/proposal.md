# Store export tokens hashed

## Why

Export tokens are stored as plaintext in `export_tokens.token`. Since subject-bound INTERNAL tokens authorize personal duty feeds (PR #579), a database leak would expose private duty-holder identities for every feed. Hashing the token at rest removes that exposure: a leaked database no longer contains usable feed credentials.

## What Changes

- Store only a SHA-256 hash of the token; the plaintext secret is returned exactly once when a token is created or rotated.
- `GET /api/v1/export-tokens` no longer returns usable token secrets; it lists metadata only.
- A `POST /api/v1/export-tokens/{id}/reveal` endpoint returns the plaintext secret once for tokens created before hashing existed (legacy plaintext rows), enabling a one-time migration to hashed storage.
- Existing plaintext tokens are migrated by hashing their stored value; already-hashed tokens are detected by a stored marker/format and left untouched.
- Feed lookup (`GET /api/v1/export/{token}/calendar.ics`) and the RLS export context hash the presented token before comparison; SQL policies compare against the hashed column.
- Frontend (`ExportTokensView.vue`, `PersonalCalendarView.vue`) shows the secret once after creation/rotation with a copy-to-clipboard affordance instead of a reusable token column.

## Capabilities

### Modified Capabilities

- `ical-export`: token storage, reveal-once lifecycle, feed lookup by hash.

## Impact

Breaking for UI flows that expect a reusable listed token. Alembic migration converts existing plaintext rows in place. No change to RBAC, token types, scoping or feed content.

## Non-goals

- Token rotation reminders or expiry policies.
- Changing token entropy (`secrets.token_urlsafe(32)` stays).
- Encrypting instead of hashing (feeds must be usable without a server-side secret store lookup beyond the hash).
