## Context

Export-token authorization spans API readers, ORM queries, row-level policies and SECURITY DEFINER helpers. The current database contract compares the presented plaintext secret with `export_tokens.token`. Replacing only the repository lookup with a hash query cannot bypass that boundary and must not be advertised as hash-only support.

## Decisions

### Keep the expand phase compatible with old readers and writers

Add nullable `token_hash` and preserve `token` unchanged. Backfill all rows, including plaintext values that happen to look hexadecimal. Hashes supplement storage; they are neither bearer credentials nor an additional RLS bypass. New rows carry both values, and older releases can still insert a null hash.

### Make the one-time response usable independently of ancillary requests

Publish creation success and the full subscription URL immediately after the POST. Fetching congregation display names is a separate operation with a separate error message. Personal event loading depends on the date range; token loading and creation depend only on district and identity. Scope changes invalidate pending requests and clear secrets held in memory.

### Defer the complete contract migration

The rollback window has no automatic timeout in this change. The follow-up tracked by #582 must first reconcile mixed-version writes and implement hash-aware readers at every authorization layer. It must test incorrect tokens, digest-as-token rejection, revoked tokens, scope revocation and cross-district access using the production runtime role. Only after those checks and operator coordination may plaintext be removed.

## Validation

Regression tests exercise absolute copy values, date changes during and after creation, failed date reloads, identity switches, pending token loads, and congregation preload failures. Backend tests verify secret-free listings. Real PostgreSQL tests exercise migration backfill and downgrade/upgrade on an isolated temporary table, plus legacy/dual-write feed authorization, digest rejection and revocation under NOBYPASSRLS.
