# Registration watcher race-condition fix (Issue #712)

## Design
Retain the public API contract. Invalidate prior watcher work through Vue's onCleanup callback, clear old choices immediately, and accept success/error only for the current request.

## Implementation
1. Add promise-controlled Vitest cases for district A then B, district A then clear, and obsolete failure.
2. Implement watcher-local cleanup and conditional application of results in RegistrationView.vue.
3. Add an OpenSpec frontend-ux capability delta.
4. Verify docs/OpenSpec, Vue type-check, Vitest coverage >=80%, E2E and lint in PR CI.

## Review focus
No cross-district options in the UI; do not change backend authorization. Ensure a stale failed request cannot hide valid current choices.
