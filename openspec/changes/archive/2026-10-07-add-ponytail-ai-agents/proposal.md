# Add Ponytail support for all repository AI agents

## Why

The repository already mirrors OpenSpec skills into the repo-local skill directories used by its AI agents. Ponytail is currently only installable through user-level CLI/plugin commands, so its coding rules are not reproducible from the repository itself.

## What Changes

- Mirror the six Ponytail v4.10.1 skills into every existing repo-local AI skill host: `.agent`, `.claude`, `.codex`, `.gemini`, `.github`, `.opencode`, and `.qwen`.
- Pin the mirrored content to upstream commit `c6ce46179874ea7368da0eb9e67c1ad5c10f08bc`.
- Preserve the upstream MIT license in a central third-party notice.
- Do not change runtime application behavior, dependencies, or production configuration.

## Impact

All configured AI coding agents can discover the same Ponytail behavior directly from the repository. The change is documentation and agent tooling only, so application code coverage is unaffected.
