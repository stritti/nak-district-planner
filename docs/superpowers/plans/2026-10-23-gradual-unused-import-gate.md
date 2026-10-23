# First stage of Ruff F401 migration (#715)

## Design
Apply Ruff F401 in a narrow pair of reviewed registration production modules without prematurely enabling it for all legacy imports. Keep project-wide lint and existing CI unchanged; add an isolated per-path gate.

## Implementation
1. Remove the unused Enum import in LeaderRegistration.
2. Add an isolated F401 Ruff command in backend CI on the domain model and HTTP adapter router.
3. Add an OpenSpec quality-gate delta; verify CI and >=80% backend coverage.

## Next stages
Track additional reviewed modules and safe intentional reexports in #715, then remove global ignore only after full Ruff and test gates pass.
