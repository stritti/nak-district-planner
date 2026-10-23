#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Stephan Strittmatter
# SPDX-License-Identifier: AGPL-3.0-only

"""Prepend release-specific production upgrade instructions to GitHub Release notes.

Only note files first added since the preceding published release tag are included.
An unresolved earlier draft or a tag without a public GitHub Release blocks a
later release rather than omitting required upgrade instructions.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
import tempfile
from pathlib import Path

NOTES_DIR = Path("docs/operations/release-notes")
HEADING = "## WICHTIG: Anpassungen bei produktiven Installationen"


def _execute(*args: str, cwd: Path, text_mode: bool) -> subprocess.CompletedProcess:
    """Run a command without shell expansion and preserve diagnostics on failure."""
    try:
        return subprocess.run(
            args, cwd=cwd, check=True, capture_output=True, text=text_mode
        )
    except subprocess.CalledProcessError as exc:
        error = exc.stderr
        if isinstance(error, bytes):
            error = error.decode("utf-8", errors="replace")
        print(
            f"Command {' '.join(args[:3])} failed with code {exc.returncode}: "
            f"{(error or '(no stderr)').strip()}",
            file=sys.stderr,
        )
        raise


def run(*args: str, cwd: Path) -> str:
    """Execute a text command and surface its stderr when it fails."""
    return _execute(*args, cwd=cwd, text_mode=True).stdout


def run_bytes(*args: str, cwd: Path) -> bytes:
    """Execute a binary command (for NUL-separated git output)."""
    return _execute(*args, cwd=cwd, text_mode=False).stdout


def previous_release_tag(repo: Path, tag: str) -> str | None:
    """Find the closest ancestor release tag, excluding the current release."""
    result = subprocess.run(
        [
            "git", "describe", "--tags", "--first-parent",
            "--match", "v[0-9]*.[0-9]*.[0-9]*", "--abbrev=0", f"{tag}^",
        ],
        cwd=repo,
        capture_output=True,
        text=True,
        check=False,
    )
    return result.stdout.strip() if result.returncode == 0 else None


def verify_previous_release_is_published(repo: Path, tag: str) -> None:
    """Do not allow a failed draft to be skipped by the next release."""
    previous = previous_release_tag(repo, tag)
    if previous is None:
        return
    # The closest ancestor tag must be a public GitHub Release. A leftover tag
    # with no Release is also unsafe: its notes must not silently become the
    # baseline for the next publication.
    is_draft = run(
        "gh", "release", "view", previous, "--json", "isDraft", "--jq", ".isDraft",
        cwd=repo,
    ).strip()
    if is_draft != "false":
        raise ValueError(
            f"Cannot publish {tag}: previous release {previous} is not publicly "
            "published. Recover and publish that draft first."
        )

def new_note_paths(repo: Path, tag: str) -> list[Path]:
    """Find notes introduced in this release; never reprint older notes."""
    run("git", "rev-parse", "--verify", f"refs/tags/{tag}^{{commit}}", cwd=repo)
    previous = previous_release_tag(repo, tag)
    if previous:
        args = (
            "git", "diff", "--diff-filter=A", "--name-only", "-z",
            previous, tag, "--", str(NOTES_DIR),
        )
    else:
        args = ("git", "ls-tree", "-r", "--name-only", "-z", tag, "--", str(NOTES_DIR))
    # NUL-separated names handle spaces and special characters.
    paths = run_bytes(*args, cwd=repo).split(b"\0")
    return sorted(Path(p.decode("utf-8")) for p in paths if p and p.endswith(b".md"))


_REQUIRED_SECTIONS = ("Betroffen", "Vor dem Update", "Nach dem Update")
_SECTION_PATTERN = re.compile(r"^\*\*(Betroffen|Vor dem Update|Nach dem Update):\*\*", re.MULTILINE)


def validate_upgrade_note(body: str, path: Path) -> None:
    """Require ordered, line-anchored sections with actionable contents."""
    sections = list(_SECTION_PATTERN.finditer(body))
    if not body.startswith("### ") or tuple(m.group(1) for m in sections) != _REQUIRED_SECTIONS:
        raise ValueError(
            f"{path}: note must start with ### and contain the ordered "
            "Betroffen, Vor dem Update and Nach dem Update sections"
        )
    for i, section in enumerate(sections):
        end = sections[i + 1].start() if i + 1 < len(sections) else len(body)
        if not body[section.end():end].strip():
            raise ValueError(f"{path}: {section.group(1)} section is empty")


def load_upgrade_notes(repo: Path, tag: str) -> list[str]:
    """Read and validate upgrade notes from the tagged snapshot."""
    notes = []
    for path in new_note_paths(repo, tag):
        body = run("git", "show", f"{tag}:{path.as_posix()}", cwd=repo).strip()
        validate_upgrade_note(body, path)
        notes.append(body)
    return notes


def compose_release_body(current: str, tag: str, notes: list[str]) -> str:
    """Insert operator actions before ordinary release-please notes, once."""
    if not notes:
        return current
    marker = f"<!-- nak-district-planner:upgrade-notes:{tag} -->"
    if marker in current:
        return current
    content = "\n\n".join(notes)
    return f"{marker}\n{HEADING}\n\n{content}\n\n---\n\n{current.lstrip()}"


def publish(repo: Path, tag: str) -> bool:
    """Update the GitHub Release only if new actionable notes were added."""
    verify_previous_release_is_published(repo, tag)
    notes = load_upgrade_notes(repo, tag)
    if not notes:
        print(f"No production configuration changes introduced in {tag}.")
        return False
    current = run("gh", "release", "view", tag, "--json", "body", "--jq", ".body", cwd=repo)
    updated = compose_release_body(current, tag, notes)
    if updated == current:
        print(f"Production upgrade notes already present in {tag}.")
        return False
    with tempfile.TemporaryDirectory(prefix="nak-upgrade-notes-") as temp:
        note_file = Path(temp) / "notes.md"
        note_file.write_text(updated, encoding="utf-8")
        run("gh", "release", "edit", tag, "--notes-file", str(note_file), cwd=repo)
    print(f"Published {len(notes)} production upgrade note(s) in {tag}.")
    return True


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tag", required=True, help="Draft GitHub release tag")
    args = parser.parse_args()
    repo = Path(__file__).resolve().parent.parent
    # Do not publish a note from an unrelated checkout.
    checked_out = run("git", "rev-parse", "HEAD", cwd=repo).strip()
    tagged = run("git", "rev-parse", f"refs/tags/{args.tag}^{{commit}}", cwd=repo).strip()
    if checked_out != tagged:
        raise SystemExit("The checkout does not match the draft release tag.")
    publish(repo, args.tag)


if __name__ == "__main__":
    main()
