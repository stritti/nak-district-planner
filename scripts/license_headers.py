#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Stephan Strittmatter
# SPDX-License-Identifier: AGPL-3.0-only

"""Validate or add SPDX headers to first-party source files."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

COPYRIGHT = "SPDX-FileCopyrightText: 2026 Stephan Strittmatter"
LICENSE = "SPDX-License-Identifier: AGPL-3.0-only"
SOURCE_PREFIXES = ("services/backend/", "services/frontend/", "idp-deploy/", "scripts/")
ROOT_SOURCES = {"verify-phase4b-compatibility.sh"}
COMMENT_STYLES = {
    ".py": "#",
    ".mako": "#",
    ".sh": "#",
    ".ts": "//",
    ".tsx": "//",
    ".mts": "//",
    ".js": "//",
    ".jsx": "//",
    ".cjs": "//",
    ".mjs": "//",
    ".vue": "html",
    ".html": "html",
    ".css": "css",
}
EXCLUDED_PREFIXES = (
    "services/frontend/playwright-report/",
    "services/frontend/dist/",
    "services/frontend/coverage/",
    "services/frontend/node_modules/",
    "services/backend/.venv/",
    "services/backend/.pytest_cache/",
)


def is_first_party_source(path: str) -> bool:
    """Only audit maintained source, never vendored or generated artifacts."""
    if path.startswith(EXCLUDED_PREFIXES):
        return False
    return (
        path in ROOT_SOURCES or path.startswith(SOURCE_PREFIXES)
    ) and Path(path).suffix in COMMENT_STYLES


def header_for(path: str) -> str:
    style = COMMENT_STYLES[Path(path).suffix]
    if style == "html":
        return f"<!-- {COPYRIGHT}\n     {LICENSE} -->\n\n"
    if style == "css":
        return f"/* {COPYRIGHT}\n * {LICENSE} */\n\n"
    return f"{style} {COPYRIGHT}\n{style} {LICENSE}\n\n"


def header_is_valid(text: str) -> bool:
    """Reject missing, conflicting, or incomplete declarations."""
    top = "\n".join(text.splitlines()[:16])
    return (
        COPYRIGHT in top
        and LICENSE in top
        and top.count("SPDX-License-Identifier:") == 1
        and top.count("SPDX-FileCopyrightText:") >= 1
    )


def annotate(text: str, path: str) -> str:
    """Preserve shebang, Python encoding declarations and HTML doctype."""
    if header_is_valid(text):
        return text
    top = "\n".join(text.splitlines()[:16])
    if "SPDX-License-Identifier:" in top or "SPDX-FileCopyrightText:" in top:
        raise ValueError(f"Conflicting SPDX metadata in {path}; review manually")
    if "Copyright" in top or "copyright" in top:
        raise ValueError(f"Existing copyright in {path}; review manually")
    bom = "\ufeff" if text.startswith("\ufeff") else ""
    if bom:
        text = text.removeprefix(bom)
    lines = text.splitlines(keepends=True)
    n = 0
    if lines and lines[0].startswith("#!"):
        n = 1
    if path.endswith(".py") and n < len(lines) and "coding:" in lines[n]:
        n += 1
    if path.endswith(".html") and lines and lines[0].lower().startswith("<!doctype"):
        n = 1
    return bom + "".join(lines[:n]) + header_for(path) + "".join(lines[n:])


def tracked_sources(root: Path) -> list[str]:
    output = subprocess.run(
        ["git", "ls-files", "-z"],
        cwd=root,
        capture_output=True,
        check=True,
    ).stdout
    return sorted(
        path for raw in output.split(b"\0")
        if raw and is_first_party_source(path := raw.decode("utf-8"))
    )


def run(root: Path, *, fix: bool) -> list[str]:
    """Return all unresolved license violations."""
    errors = []
    for name in tracked_sources(root):
        file = root / name
        try:
            original = file.read_bytes().decode("utf-8")
            if header_is_valid(original):
                continue
            if not fix:
                errors.append(f"{name}: missing or invalid SPDX copyright/license")
                continue
            updated = annotate(original, name)
            file.write_bytes(updated.encode("utf-8"))
        except (UnicodeError, OSError, ValueError) as error:
            errors.append(f"{name}: {error}")
    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument("--check", action="store_true")
    action.add_argument("--fix", action="store_true")
    options = parser.parse_args(argv)
    repo_root = Path(__file__).resolve().parent.parent
    failures = run(repo_root, fix=options.fix)
    for message in failures:
        print(message, file=sys.stderr)
    if failures:
        print(f"{len(failures)} file(s) require license review", file=sys.stderr)
        return 1
    print("First-party SPDX source headers verified")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
