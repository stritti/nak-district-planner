# Keycloak 1.6.0 compatibility warning (Issue #713)

## Design
Keep release-please generated history intact. Mark the existing migration note as breaking, render a prominent banner when such notes are published, and require CI checks for key migration instructions. Keep the operator checklist distinct from runnable tests.

## Implementation
1. Add unit tests for regular/breaking/mixed release notes and the real #699 note.
2. Add the marker-based banner in publisher without changing its idempotence.
3. Update #699 operator note and documented v1.6.0 rollout/rollback checks.
4. Add OpenSpec delta and verify Docs CI with coverage/integration unchanged.

## Review focus
No claim of automatically verified Keycloak SMTP/realm state. No manual edits to generated bot changelog. Explicit compatibility exception pending formal SemVer decision.
