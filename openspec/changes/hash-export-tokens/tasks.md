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
- [x] Verify current GitHub Actions, coverage and strict OpenSpec validation

## Separate contract follow-up (#582 remains open)

The contract phase is outside this change. It must close the rollback window, backfill mixed-version writes, update every RLS policy and SECURITY DEFINER helper, adapt ORM/repository readers, and prove anonymous feeds and scope-denial cases before removing plaintext storage. See design.md.

## Verification evidence

Code commit `7830b9c1`: [CI run 38860831749](https://github.com/stritti/nak-district-planner/actions/runs/38860831749) passed 2,199 backend unit tests (one skipped), 255 PostgreSQL integration/performance tests, and 888 frontend tests. Backend coverage is 90%; frontend statement/branch/function/line coverage is 94/89.66/91.43/95.86 percent. All nine PR workflows passed, including strict OpenSpec validation, migration checks and restore drill.
