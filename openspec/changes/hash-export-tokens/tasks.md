# Tasks

- [x] Add `token_hash` column and unique index (expand phase)
- [x] Backfill hash for existing plaintext rows
- [x] Compute hash on create; return plaintext once in creation response
- [x] Stop returning plaintext in token listing
- [x] Feed lookup with plaintext column and hash fallback
- [x] Frontend: show secret only after creation, copy affordance in personal view
- [ ] Contract phase (follow-up): drop plaintext `token` column after rollback window closes
- [ ] Verify GitHub Actions checks and review CI results
