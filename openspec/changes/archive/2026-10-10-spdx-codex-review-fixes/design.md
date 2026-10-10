# Design

The checker uses `split_preamble(text, path)` to separate leading shebang, encoding, doctype or CSS charset declarations from the source body, then requires the exact language-specific SPDX header at that location. Strings inside code cannot substitute for valid comment headers.

The optional `--fix` operation refuses any existing copyright, SPDX or conventional license declaration in leading comments or a Python module docstring. Such files require manual rights verification.

The CI checker compares the indexed modes of the original executable scripts with their documented `100755` baseline. It fails for missing or non-executable files rather than silently changing the Git index.

All these cases are covered by standard-library unit tests. The project OpenSpec is updated directly to reflect the accepted constraints.
