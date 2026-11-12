## Context

See [proposal.md](proposal.md) for motivation and [the ci-supply-chain spec](/openspec/specs/ci-supply-chain/) for the behavior contract. The current configuration has seven update entries and one CodeQL group. Bun and uv both need package-name matching; using explicit patterns also makes family boundaries visible.

## Decisions

- Use cohesive package families rather than a single ecosystem-wide update: runtime, build, testing and linting have distinct failure modes. Group Vitest with its coverage provider and Tailwind with its Vite plugin.
- Keep root documentation dependencies together in their existing Bun entry.
- Separate backend API (FastAPI/Starlette/Uvicorn/Pydantic), database, OpenTelemetry and pytest/Ruff packages. The remaining-runtime catch-all explicitly excludes those families so group ordering cannot accidentally capture them.
- Set `applies-to: version-updates` and `update-types: [minor, patch]` on every new group. Preserve the existing unfiltered CodeQL group to keep init/analyze aligned across major upgrades; exclude it from the new Actions catch-all.
- Keep containers individual: the backend has one Python base image, while the frontend and Compose images are independently deployable components with different upgrade risks. No cross-ecosystem group is introduced.
- Do not add production code or a permanent configuration-test framework. Validate the YAML against the Dependabot schema and exercise group selection for manifest packages and exceptional inputs before publication.

## Risks / Trade-offs

- One failing package blocks its related group until fixed; smaller families keep the investigation scoped.
- A patch/minor label does not guarantee compatibility, especially for pre-1.0 dependencies. Existing test, coverage and security gates still apply.
- New unmatched frontend families stay individual until deliberately classified; the backend runtime fallback groups new packages unless explicitly excluded.
- Real Dependabot resolution and resulting PRs can only be observed after this configuration reaches the default branch. Local checks validate declared rules, not the hosted resolver.

## Rollout

Merge the reviewed PR to activate the rules on the default branch. Review the next scheduled Dependabot run for the expected groups. Revert the configuration commit to restore individual updates; no data migration is required.
