#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Stephan Strittmatter
# SPDX-License-Identifier: AGPL-3.0-only

"""Prepend release-specific production upgrade instructions to GitHub Release notes.

Only note files first added since the preceding release tag are included. Existing
CHANGELOG content from release-please remains intact. No note means no modification.
"""

from __future__ import annotations

import argparse
import subprocess
import tempfile
from pathlib import Path

NOTES_DIR = Path("docs/operations/release-notes")
HEADING = "## WICHTIG: Anpassungen bei produktiven Installationen"


def run(*args: str, cwd: Path) -> str:
    """Execute a command safely with argv, without shell expansion."""
    return subprocess.run(args, cwd=cwd, check=True, capture_output=True, text=True).stdout


def previous_release_tag(repo: Path, tag: str) -> str | None:
    """Find the closest ancestor release tag, excluding the current release."""
    result = subprocess.run(
        ["git", "describe", "--tags", "--abbrev=0", f"{tag}^"],
        cwd=repo,
        capture_output=True,
        text=True,
        check=False,
    )
    return result.stdout.strip() if result.returncode == 0 else None


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
    paths = subprocess.run(args, cwd=repo, check=True, capture_output=True).stdout.split(b"\0")
    return sorted(Path(p.decode("utf-8")) for p in paths if p and p.endswith(b".md"))


def load_upgrade_notes(repo: Path, tag: str) -> list[str]:
    """Read and validate upgrade notes from the tagged snapshot."""
    notes = []
    for path in new_note_paths(repo, tag):
        body = run("git", "show", f"{tag}:{path.as_posix()}", cwd=repo).strip()
        if not body.startswith("### ") or not all(
            label in body for label in (
                "**Betroffen:**", "**Vor dem Update:**", "**Nach dem Update:**",
            )
        ):
            raise ValueError(
                f"{path}: note must start with ### and include Betroffen, "
                "Vor dem Update and Nach dem Update sections"
            )
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
    parser.add_argument("--tag", required=True, help="Published GitHub release tag")
    args = parser.parse_args()
    repo = Path(__file__).resolve().parent.parent
    # Do not publish a note from an unrelated checkout.
    checked_out = run("git", "rev-parse", "HEAD", cwd=repo).strip()
    tagged = run("git", "rev-parse", f"refs/tags/{args.tag}^{{commit}}", cwd=repo).strip()
    if checked_out != tagged:
        raise SystemExit("The checkout does not match the published release tag.")
    publish(repo, args.tag)


if __name__ == "__main__":
    main()
