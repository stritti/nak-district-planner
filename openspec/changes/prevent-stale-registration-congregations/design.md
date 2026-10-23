## Context
The public registration form watches `form.district_id`. Requests for congregations can resolve out of order, and the old async callback unconditionally updates the UI.

## Decision
Use Vue 3's synchronous watcher cleanup registration (`onCleanup`) to invalidate the prior response. Always reset the congregation selection and visible options when a district changes. Both success and failure handlers check the same request-local validity flag.

## Alternatives
- An AbortController requires extending the public API client contract and still handling non-abortable responses. Not necessary.
- A global monotonically increasing request ID works but duplicates Vue's existing watcher invalidation lifecycle.

## Test strategy
Use controllable promises to reproduce A-slow/B-fast, A-slow/clear and rejection from obsolete A after B loads. Preserve frontend's >=80% per-file coverage gate.
