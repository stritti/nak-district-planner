# Prepare export-token hash storage with a safe expand phase

## Why

Export tokens currently remain reusable secrets in the database. #582 tracks replacing plaintext storage to reduce exposure after a database leak. A direct destructive migration breaks existing calendar subscriptions when the application is rolled back.

## What Changes

This change delivers only the rollback-compatible **expand phase**:

- Add a nullable, uniquely indexed SHA-256 `token_hash` column and backfill every existing plaintext token.
- New writers persist both the original secret in `token` and its digest in `token_hash`. Older application versions may continue writing rows with no hash.
- Keep plaintext lookup and the existing RLS session-token contract authoritative. A digest is not accepted as a feed credential. This phase does not claim hash-only feed support.
- Return the secret only in the creation response. Listings return metadata, including `token: null`.
- Offer an absolute, copyable subscription URL immediately after creation. Event-date changes and ancillary name-loading failures must not discard that URL; an identity or district switch must clear it.
- Document migration ordering, rollback compatibility and the impact on links that have not been copied.

## Capabilities

### Modified Capabilities

- `ical-export`: additive hash storage, one-time creation response and preserved feed compatibility.

## Impact

The UI can no longer reconstruct an existing link from listings; already subscribed calendars continue using their original URL. The migration must run before the new backend starts. RBAC, RLS policies, token types and feed content remain unchanged.

**Security limitation:** plaintext remains in the database during this phase. #582 stays open; this release does not yet protect export secrets against a database leak.

## Follow-up: contract phase

After an explicitly closed rollback window, a separate change must backfill rows written by older versions, update every RLS policy and SECURITY DEFINER helper to verify hashes, adapt ORM/repository readers, prove anonymous personal and district feeds under NOBYPASSRLS, and only then remove plaintext storage. Dropping a column alone is not sufficient.

## Non-goals

- Completing the contract phase or offering a reveal endpoint.
- Changing token entropy, rotation or expiry policies.
