# Expand-phase tasks

- [x] Add nullable hash column and unique index; preserve plaintext for rollback
- [x] Backfill every plaintext row, including hexadecimal-looking secrets
- [x] Keep plaintext lookup and RLS authoritative; remove unsupported hash fallback
- [x] Return secrets only in creation responses and cover metadata-only listings
- [x] Offer complete personal subscription URLs and preserve them across date reloads
- [x] Separate token creation success from congregation display-name loading
- [x] Test identity switches, stale responses, failed reloads and pending creation
- [x] Add PostgreSQL migration roundtrip and runtime-role authorization tests
- [x] Document operator upgrade steps and the security limitation
- [ ] Verify current GitHub Actions, coverage and strict OpenSpec validation

## Separate contract follow-up (#582 remains open)

The contract phase is outside this change. It must close the rollback window, backfill mixed-version writes, update every RLS policy and SECURITY DEFINER helper, adapt ORM/repository readers, and prove anonymous feeds and scope-denial cases before removing plaintext storage. See design.md.
