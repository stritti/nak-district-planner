## Why

The demo district gives every planning situation a concrete example, but the VitePress documentation only explains the rules in the abstract. Docs also drift: nothing reminds a change to update the pages that describe the behaviour it alters.

## What Changes

- New page `docs/guide/demo-district.md` ("Rundgang mit dem Demo-Bezirk"): the seven getting-started steps walked through with the demo district's congregations, leaders, conflicts per week, release, calendar subscription and holidays. Linked from the sidebar, the start page, the workflows guide, the conflict rules and the documentation map.
- `tests/unit/test_seed_demo.py` checks the walkthrough against the seed: district, congregations with service times, leaders, organist, token label, number of services and each conflict rule in its week. CI runs the backend tests when the walkthrough changes.
- `openspec/config.yaml` rules ask every proposal to name the affected docs pages and every task list to update them, including seed and walkthrough together.

## Impact

- Docs: `docs/guide/demo-district.md` (new), `docs/guide/workflows.md`, `docs/features/conflict-rules.md`, `docs/index.md`, `docs/documentation-map.md`, `docs/.vitepress/config.mts`.
- Backend tests and the CI path filter; no product behaviour changes.
