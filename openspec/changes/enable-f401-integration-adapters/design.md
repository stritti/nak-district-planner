## Scope and verification approach
Use the pinned Ruff invoked as `uv run ruff check --isolated --select F401` in the existing backend CI, with all six adapter directories appended to previously protected paths. Ruff's `--isolated` option ensures the repository-level F401 ignore cannot silently disable this gate.

## Existing safety behavior
No code imports or exports change in this PR; the modules that handle OIDC, authentication, mail and workers keep their import-time dependencies and runtime side effects intact. Full backend unit tests with exception paths, PostgreSQL RLS integration and frontend tests are required.

## Verification evidence
- Initial `auth`, `idp`, `mail`, and `version_check` gate in CI run 40087254789 successfully detected no F401 violations.
- The expanded scope also covers `calendar` and `worker`; the first full-gate run is 40087353556. On this initial head Ruff F401 passed without unused imports, so no production imports are removed.
- A previously demonstrated negative test of the unchanged isolated Ruff rule is available in issue #715 (CI runs 40086639329 and 40030528685, both failed on actual unused imports). A new rule invocation is not created in this PR.

## Remaining work
PR #722 has merged: the conflict with its `app/application` addition is resolved by preserving both the full application directory and these six adapter directories in the same gate. Security issue #723 is closed after PR #725 and an entirely successful `main` Security Scans workflow. Remaining adapter API/DB modules and test modules must be audited before the global F401 ignore can be removed.
