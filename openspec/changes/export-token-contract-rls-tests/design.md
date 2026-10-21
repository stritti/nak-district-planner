# Export Token Contract RLS Verification

## Baseline

`tests/integration/test_export_token_contract_upgrade_postgres.py` creates an isolated database, seeds legacy plaintext tokens as an owner, upgrades across `20261016_contract_export_tokens`, and checks that `token` disappears. `tests/integration/test_rls_postgres.py` provides a working pattern to connect as the non-owner NOBYPASSRLS application role using `RLS_TEST_DATABASE_URL`, `RLS_TEST_APP_PASSWORD` and `APP_DB_USER`. CI already provisions PostgreSQL and sets both RLS variables.

## Test architecture

Re-use the disposable migration fixture, never write to an operator database. Seed two distinct districts with valid membership/subject contexts and realistic planning slots, as well as legacy PUBLIC, INTERNAL and person-scoped feeds. Use a restricted-application connection created explicitly with the role credentials, asserting `rolsuper = false`, `rolbypassrls = false`, and that it does not own the protected tables. Each query is performed in its own transaction with the same `app.current_export_token` and `app.current_user_sub` GUCs used in production.

Define an expectation matrix to assert which token permits reading which rows: a PUBLIC feed only the published public scope; INTERNAL and PERSONAL according to their existing policy, with no cross-district visibility; revoked and unknown tokens show nothing. Include a negative test where a legitimate token is presented with another tenant's subject/context and a fail-closed token with no current user. Keep the current permission semantics as the oracle; do not assume that every token type grants the same capabilities.

Compare active `pg_policies` and `pg_proc` functions against the repository's current audit snapshot or normalize an explicit source-of-truth snapshot from the existing policy definitions. Assert no regex/AST reference to `export_tokens.token` and no `DROP COLUMN CASCADE` regression. Changes to expected definitions require explicit review rather than updating the snapshot automatically.

CI runs the regression in the existing PostgreSQL integration stage, fails rather than silently skips when credentials are expected, reports individual scenario names and cleans the disposable database in `finally`. Preserve existing upgrade and mismatch-rollback tests unchanged.

## Scope and performance

No production schema behavior change. The main risk is false confidence from owner/superuser connections or incorrectly initialized per-transaction GUCs; both are asserted explicitly. Tests cover missing and incorrect credentials as setup errors, not passing skips.

## Verification

Run the existing migration suite and new restricted-role tests on PostgreSQL 18; run all integration and unit tests; backend coverage >=80%.
