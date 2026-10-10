#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Stephan Strittmatter
# SPDX-License-Identifier: AGPL-3.0-only

"""Validate or add SPDX headers to first-party source files."""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

COPYRIGHT = "SPDX-FileCopyrightText: 2026 Stephan Strittmatter"
LICENSE = "SPDX-License-Identifier: AGPL-3.0-only"
SOURCE_PREFIXES = ("services/backend/", "services/frontend/", "idp-deploy/", "scripts/", "docs/.vitepress/")
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
    "docs/.vitepress/dist/",
    "docs/.vitepress/cache/",
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


# PEP 263 allows an encoding cookie on either of the first two lines.
_PYTHON_ENCODING = re.compile(r"^[ \t\f]*#.*?coding[:=][ \t]*[-_.a-zA-Z0-9]+")
_CSS_CHARSET = re.compile(r'^@charset\s+["\x27][^"\x27]+["\x27]\s*;')
def comment_texts(text: str, *, limit: int = 50) -> list[str]:
    """Extract line and multiline comment bodies without HTML-filter regexes."""
    bodies: list[str] = []
    close: str | None = None
    block: list[str] = []
    for line in text.removeprefix("\ufeff").splitlines()[:limit]:
        stripped = line.lstrip()
        if close is not None:
            end = stripped.find(close)
            if end < 0:
                block.append(stripped)
            else:
                block.append(stripped[:end])
                bodies.append(" ".join(block))
                block = []
                close = None
            continue
        for opening, ending in (("<!--", "-->"), ("/*", "*/")):
            if stripped.startswith(opening):
                content = stripped[len(opening):]
                end = content.find(ending)
                if end >= 0:
                    bodies.append(content[:end])
                else:
                    close = ending
                    block = [content]
                break
        else:
            if stripped.startswith("//"):
                bodies.append(stripped[2:])
            elif stripped.startswith("#"):
                bodies.append(stripped[1:])
    if block:
        bodies.append(" ".join(block))
    return bodies
_LEGAL_NOTICE = re.compile(
    r"SPDX-(?:License-Identifier|FileCopyrightText):"
    r"|\bcopyright\b|\blicensed under\b|\blicen[cs]e\s*:"
    r"|\b(?:MIT|Apache|BSD|GPL|AGPL)\s+licen[cs]e\b",
    re.IGNORECASE,
)
# These original file modes existed before the AGPL header migration.
EXECUTABLE_SCRIPTS = (
    "idp-deploy/authentik/deploy_authentik.sh",
    "idp-deploy/authentik/import_blueprint.py",
    "idp-deploy/authentik/setup_authentik_oauth2.py",
    "idp-deploy/keycloak/deploy_keycloak.sh",
    "idp-deploy/keycloak/setup_keycloak_realm.py",
    "idp-deploy/test-oidc-integration.sh",
    "scripts/backup.sh",
    "scripts/restore.sh",
    "services/frontend/15-real-ip-from.sh",
    "verify-phase4b-compatibility.sh",
)


def split_preamble(text: str, path: str) -> tuple[str, str]:
    """Retain the required initial directives before adding a source comment."""
    bom = "\ufeff" if text.startswith("\ufeff") else ""
    content = text.removeprefix(bom) if bom else text
    lines = content.splitlines(keepends=True)
    keep = 1 if lines and lines[0].startswith("#!") else 0
    if path.endswith(".py"):
        for position in range(min(2, len(lines))):
            if _PYTHON_ENCODING.match(lines[position]):
                keep = max(keep, position + 1)
                break
    if path.endswith(".html") and lines and lines[0].lower().startswith("<!doctype"):
        keep = 1
    if path.endswith(".css") and lines and _CSS_CHARSET.match(lines[0]):
        keep = 1
    return bom + "".join(lines[:keep]), "".join(lines[keep:])


def _leading_notice(text: str, path: str) -> bool:
    """Prevent an automatic relicense if any prior legal notice exists."""
    if any(_LEGAL_NOTICE.search(comment) for comment in comment_texts(text)):
        return True
    # A Python module-level docstring can also contain the original license.
    _, body = split_preamble(text, path)
    document = body.lstrip()
    if document.startswith(('"""', "'''")):
        quote = document[:3]
        end = document.find(quote, 3)
        if end > 0 and _LEGAL_NOTICE.search(document[3:end]):
            return True
    return False


def header_is_valid(text: str, path: str) -> bool:
    """Validate the exact SPDX header in this source language's comment syntax."""
    if Path(path).suffix not in COMMENT_STYLES:
        return False
    _, contents = split_preamble(text, path)
    header = header_for(path)
    if not contents.startswith(header):
        return False
    # Duplicate SPDX metadata in a nearby comment creates ambiguous attribution.
    tail = contents[len(header):]
    return not any(
        re.match(r"\s*SPDX-(?:License-Identifier|FileCopyrightText):", comment)
        for comment in comment_texts(tail, limit=16)
    )


def annotate(text: str, path: str) -> str:
    """Idempotently annotate a source without overwriting existing notices."""
    if header_is_valid(text, path):
        return text
    if _leading_notice(text, path):
        raise ValueError(f"Existing copyright or license notice in {path}; review manually")
    preamble, body = split_preamble(text, path)
    return preamble + header_for(path) + body


def executable_mode_errors(root: Path) -> list[str]:
    """Ensure executable scripts remain executable in Git's index."""
    output = subprocess.run(
        ["git", "ls-files", "--stage", "-z", "--", *EXECUTABLE_SCRIPTS],
        cwd=root,
        capture_output=True,
        check=True,
    ).stdout
    actual = {}
    for entry in output.split(b"\0"):
        if not entry:
            continue
        mode_and_hash, file = entry.split(b"\t", 1)
        actual[file.decode("utf-8")] = mode_and_hash.split(b" ", 1)[0].decode("ascii")
    return [
        f"{path}: executable mode 100755 required (found {actual.get(path, 'missing')})"
        for path in EXECUTABLE_SCRIPTS
        if actual.get(path) != "100755"
    ]


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
            if header_is_valid(original, name):
                continue
            if not fix:
                errors.append(f"{name}: missing or invalid SPDX copyright/license")
                continue
            updated = annotate(original, name)
            file.write_bytes(updated.encode("utf-8"))
        except (UnicodeError, OSError, ValueError) as error:
            errors.append(f"{name}: {error}")
    errors.extend(executable_mode_errors(root))
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
