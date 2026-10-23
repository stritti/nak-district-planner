# SPDX-FileCopyrightText: 2026 Stephan Strittmatter
# SPDX-License-Identifier: AGPL-3.0-only

"""Behavioral tests for publishing actionable release-specific upgrade notes."""

from __future__ import annotations

import contextlib
import io
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.publish_release_upgrade_notes import (
    HEADING,
    NOTES_DIR,
    compose_release_body,
    load_upgrade_notes,
    new_note_paths,
    previous_release_tag,
    publish,
    run,
    validate_upgrade_note,
    verify_previous_release_is_published,
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

    def commit(self, message: str, tag: str | None = None, *, allow_empty: bool = False) -> None:
        self.git("add", ".")
        args = ("commit", "-qm", message, "--allow-empty") if allow_empty else ("commit", "-qm", message)
        self.git(*args)
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
        with patch("scripts.publish_release_upgrade_notes.verify_previous_release_is_published"):
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
        diagnostics = io.StringIO()
        with contextlib.redirect_stderr(diagnostics):
            with self.assertRaises(subprocess.CalledProcessError):
                new_note_paths(self.repo, "v100.0.0")
        self.assertIn("failed with code", diagnostics.getvalue())

    def test_nonrelease_tag_does_not_interrupt_upgrade_note_range(self) -> None:
        self.note("first.md")
        self.commit("First upgrade", tag="v1.0.1")
        self.git("tag", "test-build-artifact")
        self.note("second.md")
        self.commit("Second upgrade", tag="v1.0.2")
        self.assertEqual(previous_release_tag(self.repo, "v1.0.2"), "v1.0.1")
        self.assertEqual(
            [p.name for p in new_note_paths(self.repo, "v1.0.2")], ["second.md"]
        )

    def test_unpublished_predecessor_blocks_later_release(self) -> None:
        self.note()
        self.commit("Unresolved draft", tag="v1.0.1")
        self.commit("Later version", tag="v1.0.2", allow_empty=True)
        with patch("scripts.publish_release_upgrade_notes.run", return_value="true") as gh:
            with self.assertRaisesRegex(ValueError, "Recover and publish that draft first"):
                publish(self.repo, "v1.0.2")
        gh.assert_called_once_with(
            "gh", "release", "view", "v1.0.1", "--json", "isDraft", "--jq", ".isDraft",
            cwd=self.repo,
        )

    def test_missing_predecessor_release_blocks_later_release(self) -> None:
        self.commit("Orphaned release tag", tag="v1.0.1", allow_empty=True)
        self.commit("Later version", tag="v1.0.2", allow_empty=True)
        missing = subprocess.CalledProcessError(1, ["gh", "release", "view"])
        with patch("scripts.publish_release_upgrade_notes.run", side_effect=missing):
            with self.assertRaises(subprocess.CalledProcessError):
                publish(self.repo, "v1.0.2")

    def test_resolved_draft_allows_future_release(self) -> None:
        self.note()
        self.commit("Published predecessor", tag="v1.0.1")
        self.commit("Later version", tag="v1.0.2", allow_empty=True)
        with patch("scripts.publish_release_upgrade_notes.run", return_value="false"):
            verify_previous_release_is_published(self.repo, "v1.0.2")

    def test_retry_of_same_draft_accepts_published_predecessor(self) -> None:
        self.commit("Draft retry", tag="v1.0.1", allow_empty=True)
        with patch("scripts.publish_release_upgrade_notes.run", return_value="false"):
            self.assertFalse(publish(self.repo, "v1.0.1"))

    def test_initial_release_without_predecessor_requires_no_api_call(self) -> None:
        with patch("scripts.publish_release_upgrade_notes.run") as gh:
            verify_previous_release_is_published(self.repo, "v1.0.0")
        gh.assert_not_called()
    def test_labels_mentioned_mid_paragraph_are_not_valid_sections(self) -> None:
        with self.assertRaisesRegex(ValueError, "Betroffen"):
            validate_upgrade_note(
                "### Update\n\nSome prose mentions **Betroffen:** inline\n"
                "**Vor dem Update:** Setup\n**Nach dem Update:** Checks\n",
                Path("misleading.md"),
            )

    def test_empty_action_section_fails_closed(self) -> None:
        with self.assertRaisesRegex(ValueError, "Vor dem Update section is empty"):
            validate_upgrade_note(
                "### Update\n\n**Betroffen:** Production\n\n"
                "**Vor dem Update:**\n\n**Nach dem Update:** Verify\n",
                Path("empty.md"),
            )

    def test_command_errors_include_stderr(self) -> None:
        problem = subprocess.CalledProcessError(
            2, ["gh", "release", "edit"], stderr="permission denied"
        )
        diagnostics = io.StringIO()
        with patch("scripts.publish_release_upgrade_notes.subprocess.run", side_effect=problem):
            with contextlib.redirect_stderr(diagnostics):
                with self.assertRaises(subprocess.CalledProcessError):
                    run("gh", "release", "edit", cwd=self.repo)
        self.assertIn("permission denied", diagnostics.getvalue())

    def test_publication_keeps_original_generated_changelog(self) -> None:
        self.note()
        self.commit("New note", tag="v1.0.1")
        captured: dict[str, str] = {}

        def fake_run(*args: str, cwd: Path) -> str:
            if args[:3] == ("gh", "release", "view"):
                if "--json" in args and "isDraft" in args:
                    return "false"
                return "### Features\n\nExisting changelog\n"
            if args[:3] == ("gh", "release", "edit"):
                captured["body"] = Path(args[5]).read_text(encoding="utf-8")
                return ""
            return run(*args, cwd=cwd)

        with patch("scripts.publish_release_upgrade_notes.run", side_effect=fake_run):
            self.assertTrue(publish(self.repo, "v1.0.1"))
        self.assertIn("**Vor dem Update:**", captured["body"])
        self.assertIn("Existing changelog", captured["body"])


if __name__ == "__main__":
    unittest.main()


class CommittedUpgradeNotesTests(unittest.TestCase):
    """A malformed note fails the release job after the tag exists, so catch it in CI."""

    def test_every_committed_note_is_publishable(self) -> None:
        repo = Path(__file__).resolve().parent.parent
        paths = sorted((repo / NOTES_DIR).glob("*.md"))
        self.assertTrue(paths)
        for path in paths:
            with self.subTest(note=path.name):
                validate_upgrade_note(path.read_text(encoding="utf-8").strip(), path)
