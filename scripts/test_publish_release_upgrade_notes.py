# SPDX-FileCopyrightText: 2026 Stephan Strittmatter
# SPDX-License-Identifier: AGPL-3.0-only

"""Behavioral tests for publishing actionable release-specific upgrade notes."""

from __future__ import annotations

import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from publish_release_upgrade_notes import (
    HEADING,
    NOTES_DIR,
    compose_release_body,
    load_upgrade_notes,
    new_note_paths,
    previous_release_tag,
    publish,
    run,
)


class ReleaseUpgradeNotesTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.repo = Path(self.temp.name)
        self.git("init", "-q")
        self.git("config", "user.email", "tests@example.invalid")
        self.git("config", "user.name", "Release Tests")
        (self.repo / "README.md").write_text("Initial\n", encoding="utf-8")
        self.commit("Initial release", tag="v1.0.0")

    def git(self, *args: str) -> str:
        return subprocess.run(
            ["git", *args], cwd=self.repo, capture_output=True, text=True, check=True
        ).stdout.strip()

    def commit(self, message: str, tag: str | None = None) -> None:
        self.git("add", ".")
        self.git("commit", "-qm", message)
        if tag:
            self.git("tag", tag)

    def note(self, name: str = "472-hardening.md", *, content: str | None = None) -> None:
        path = self.repo / NOTES_DIR / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            content
            or "### Produktiv-Update #472\n\n**Betroffen:** Produktion\n\n"
            "**Vor dem Update:** Passwort setzen\n\n**Nach dem Update:** Health prüfen\n",
            encoding="utf-8",
        )

    def test_note_is_published_at_top_and_is_idempotent(self) -> None:
        self.note()
        self.commit("Add configuration upgrade note", tag="v1.0.1")
        notes = load_upgrade_notes(self.repo, "v1.0.1")
        original = "## [1.0.1]\n\n### Bug Fixes\n..."
        result = compose_release_body(original, "v1.0.1", notes)
        self.assertTrue(result.startswith("<!-- nak-district-planner:upgrade-notes:v1.0.1 -->"))
        self.assertIn(HEADING, result)
        self.assertIn("**Vor dem Update:**", result)
        self.assertTrue(result.endswith(original))
        self.assertEqual(compose_release_body(result, "v1.0.1", notes), result)

    def test_no_upgrade_note_does_not_touch_release_description(self) -> None:
        self.assertEqual(new_note_paths(self.repo, "v1.0.0"), [])
        self.assertEqual(compose_release_body("existing text", "v1.0.0", []), "existing text")

    def test_old_notes_are_not_republished_or_changed_notes_repeated(self) -> None:
        self.note()
        self.commit("Add upgrade note", tag="v1.0.1")
        self.note(
            content="### Different\n\n**Betroffen:** Ops\n\n"
            "**Vor dem Update:** A\n\n**Nach dem Update:** B\n"
        )
        self.commit("Improve old note", tag="v1.0.2")
        self.assertEqual(new_note_paths(self.repo, "v1.0.2"), [])
        self.assertEqual(previous_release_tag(self.repo, "v1.0.2"), "v1.0.1")
        self.assertFalse(publish(self.repo, "v1.0.2"))

    def test_multiple_new_notes_have_deterministic_order(self) -> None:
        self.note("b.md")
        self.note("a.md")
        self.commit("Multiple upgrade notes", tag="v1.0.1")
        self.assertEqual(
            [p.name for p in new_note_paths(self.repo, "v1.0.1")],
            ["a.md", "b.md"],
        )

    def test_invalid_operator_note_fails_closed(self) -> None:
        self.note(content="### Change without actionable guidance\n")
        self.commit("Incomplete upgrade note", tag="v1.0.1")
        with self.assertRaisesRegex(ValueError, "Betroffen"):
            load_upgrade_notes(self.repo, "v1.0.1")

    def test_missing_tag_fails_closed(self) -> None:
        with self.assertRaises(subprocess.CalledProcessError):
            new_note_paths(self.repo, "v100.0.0")

    def test_publication_keeps_original_generated_changelog(self) -> None:
        self.note()
        self.commit("New note", tag="v1.0.1")
        captured: dict[str, str] = {}

        def fake_run(*args: str, cwd: Path) -> str:
            if args[:3] == ("gh", "release", "view"):
                return "### Features\n\nExisting changelog\n"
            if args[:3] == ("gh", "release", "edit"):
                captured["body"] = Path(args[5]).read_text(encoding="utf-8")
                return ""
            return run(*args, cwd=cwd)

        with patch("publish_release_upgrade_notes.run", side_effect=fake_run):
            self.assertTrue(publish(self.repo, "v1.0.1"))
        self.assertIn("**Vor dem Update:**", captured["body"])
        self.assertIn("Existing changelog", captured["body"])


if __name__ == "__main__":
    unittest.main()
