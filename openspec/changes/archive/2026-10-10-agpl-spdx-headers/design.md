# Design

Use two standard SPDX lines in a language-appropriate comment header. A small standard-library Python utility enumerates tracked source files with `git ls-files`, supports idempotent `--fix` and non-mutating `--check`, and refuses to overwrite conflicting existing copyright or license notices. GitHub Actions runs unit tests and the check on pushes and pull requests. The repository LICENSE is the unchanged GNU AGPLv3 text. Existing MIT files under `third_party/` and AI skills are excluded.
