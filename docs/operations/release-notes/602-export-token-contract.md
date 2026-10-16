# Export tokens: final hash-only contract (#602)

This is a **one-way** production migration. Plan a maintenance window, take and
verify an encrypted pre-contract backup, stop API/worker/beat and run the
migration with the **new** artifact before restarting it. Old backend versions
still query `export_tokens.token` and are incompatible after the contract.

Upgrade: run `20261016_contract_export_tokens` after
`20261015_hash_export_tokens`, backfilling all legacy and mixed-version rows.
Any existing mismatched digest aborts the transaction; investigate rather than
silently accepting a substituted token. SQL RLS, SECURITY DEFINER functions,
repository and ORM must be deployed together. Validate an existing PUBLIC,
INTERNAL and subject-bound ICS subscription, a revoked token and an unknown
token after the upgrade. Existing URL strings remain unchanged.

**Rollback:** Alembic downgrade deliberately fails. It is impossible to
reconstruct the token plaintext from SHA-256. A rollback requires restoring
the encrypted pre-contract backup and the matching old application version,
with the acknowledged loss of intervening writes. If a database backup cannot
be restored, rotate and redistribute affected calendar subscriptions before
starting an older version.

Dropping a column does not immediately scrub historical WAL, old backups,
database pages, or centralized access logs. Apply configured retention,
sanitized logging and a maintenance-time physical-table rewrite if the threat
model requires removing residual pages. Do not include raw tokens in audit logs.
The irreversible schema upgrade must not race a second Alembic head; if #601
merges first, rebase this PR and update its down_revision to the new head.
