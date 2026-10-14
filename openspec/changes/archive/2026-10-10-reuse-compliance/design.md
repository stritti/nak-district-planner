# Design

1. `REUSE.toml` (schema 1) assigns default AGPL-3.0-only copyright to otherwise unannotated project material with `precedence = "closest"`, preserving SPDX headers already embedded in maintained sources.
2. Imported OpenSpec and Ponytail agents use precise path-pattern `override` entries with MIT copyright attribution to upstream contributors. Other explicitly MIT skills receive dedicated overrides.
3. The project retains its root `LICENSE` while placing the identical license under `LICENSES/AGPL-3.0-only.txt`, and copies the existing third-party MIT notice into `LICENSES/MIT.txt`.
4. CI pins REUSE CLI 6.2.0, runs `reuse lint`, and separately runs the existing source-header and executable-mode checks.
5. Python standard-library tests assert declared overrides and complete text fidelity.

Imported content with uncertain provenance still requires manual rights verification; automatic file classification is not a transfer of copyright.
