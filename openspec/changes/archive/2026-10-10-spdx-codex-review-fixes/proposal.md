# Repair SPDX and copyright attribution checks

## Why

Codex review of PR #559 identified executable-mode regressions and shortcomings in the SPDX checker. PR #559 was merged before the findings were resolved.

## What changes

- Restore exactly eight executable file modes to their pre-migration state.
- Validate the canonical SPDX header using language-specific comment syntax.
- Reject existing third-party license notices including non-SPDX notices.
- Preserve Python `coding=` cookies and CSS `@charset` prologs.
- Keep VitePress source under the enforced source policy.
- Add regression tests and update the canonical license-attribution specification.

## Non-goals

No change to the repository license, business logic, dependencies or third-party copyright ownership.
