# Store export tokens hashed

## Why

Export tokens are stored as plaintext in `export_tokens.token`. Since subject-bound INTERNAL tokens authorize personal duty feeds (PR #579), a database leak would expose private duty-holder identities for every feed. A hash digest at rest removes that exposure once the plaintext column is contracted away.

## What Changes

Expand/contract rollout:

- **Expand (this change):** add a nullable `token_hash` column (SHA-256 hex) with a unique index; backfill it for existing rows. New tokens store plaintext in `token` (rollback compatibility) plus their hash in `token_hash`.
- **Readers:** feed lookup prefers the plaintext column and falls back to the hash column, so both hash-aware and hash-unaware releases work during rollout; the RLS export context still carries the presented plaintext and all existing policies stay untouched.
- **Secret exposure:** `GET /api/v1/export-tokens` lists metadata without the secret; the plaintext is returned exactly once in the creation response.
- **Contract (follow-up revision after the rollback window closes):** drop the plaintext `token` column and require `token_hash`; the hash-only lookup path is already exercised by this change.

## Capabilities

### Modified Capabilities

- `ical-export`: token hash column, secret-once lifecycle, feed lookup with hash fallback.

## Impact

Breaking for UI flows that expect a reusable listed token. Rollback to a hash-unaware release keeps every existing ICS subscription working because the plaintext column survives the expand phase. No change to RBAC, token types, scoping, RLS policies or feed content.

## Non-goals

- Token rotation reminders or expiry policies.
- Changing token entropy (`secrets.token_urlsafe(32)` stays).
- Encrypting instead of hashing (feeds must remain verifiable without a server-side secret store beyond the digest).
