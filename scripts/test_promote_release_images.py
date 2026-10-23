#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Stephan Strittmatter
# SPDX-License-Identifier: AGPL-3.0-only

"""Registry and GitHub failure-path tests for the release-readiness gate."""

from __future__ import annotations

import unittest
from unittest.mock import patch

from scripts.promote_release_images import PromotionError, ReleasePromoter, command, newer_semver

BACKEND = "sha256:" + "a" * 64
FRONTEND = "sha256:" + "b" * 64
PREVIOUS = "sha256:" + "c" * 64
REGISTRY = "ghcr.io/stritti/nak-district-planner"


class FakePublisher:
    def __init__(self, *, tag="v1.2.3"):
        self.promoter = ReleasePromoter(REGISTRY, tag, BACKEND, FRONTEND)
        self.tags = {}
        self.sources = {BACKEND, FRONTEND, PREVIOUS}
        self.draft = True
        self.published = False
        self.calls = []
        self.fail_tag = None
        self.fail_publish = False
        self.published_tags = ""
        self.supersede_during_promotion = False
        self.api_checks = 0

    def digest_of(self, ref):
        if "@" in ref:
            return ref.rsplit("@", 1)[1] if ref.rsplit("@", 1)[1] in self.sources else None
        return self.tags.get(ref)

    def tag_image(self, repo, tag, digest):
        self.calls.append((repo, tag, digest))
        self.tags[f"{repo}:{tag}"] = digest
        if self.fail_tag == (repo, tag, digest):
            raise PromotionError("Registry push failed")

    def ensure_draft(self):
        if not self.draft:
            raise PromotionError("Not a draft")

    def command(self, *args):
        if args[:2] == ("gh", "api"):
            self.api_checks += 1
            if self.supersede_during_promotion and self.api_checks == 2:
                return "v1.2.4"
            return self.published_tags
        if self.fail_publish:
            raise PromotionError("GitHub release edit failed")
        self.published = True
        self.draft = False

    def execute(self):
        with patch.object(self.promoter, "digest_of", self.digest_of), \
                patch.object(self.promoter, "tag_image", self.tag_image), \
                patch.object(self.promoter, "ensure_draft", self.ensure_draft), \
                patch("scripts.promote_release_images.command", side_effect=self.command):
            self.promoter.run()


class PromotionTests(unittest.TestCase):
    def test_stable_release_promotes_both_images_before_any_alias(self):
        fake = FakePublisher()
        fake.execute()
        self.assertTrue(fake.published)
        self.assertEqual([call[1] for call in fake.calls[:2]], ["1.2.3", "1.2.3"])
        self.assertEqual(len(fake.calls), 8)
        for service, digest in (("backend", BACKEND), ("frontend", FRONTEND)):
            self.assertEqual(fake.tags[f"{REGISTRY}/{service}:latest"], digest)

    def test_rc_does_not_modify_stable_aliases(self):
        fake = FakePublisher(tag="v1.2.3-rc.1")
        fake.execute()
        self.assertEqual([call[1] for call in fake.calls], ["1.2.3-rc.1"] * 2)

    def test_semver_precedence_handles_numeric_and_prerelease_order(self):
        cases = (
            ("v1.2.10", "v1.2.9", True),
            ("v1.2.3-rc.10", "v1.2.3-rc.2", True),
            ("v1.2.3", "v1.2.3-rc.2", True),
            ("v1.2.3-rc.1", "v1.2.3", False),
            ("v1.2.3-alpha", "v1.2.3-beta", False),
            ("v1.2.3-rc.1.1", "v1.2.3-rc.1", True),
            ("v1.2.3", "v1.2.3", False),
            ("nonsense", "v1.2.3", False),
        )
        for candidate, current, expected in cases:
            with self.subTest(candidate=candidate, current=current):
                self.assertIs(newer_semver(candidate, current), expected)

    def test_recovery_of_superseded_draft_never_changes_aliases(self):
        fake = FakePublisher()
        fake.published_tags = "v1.2.4"
        for service in ("backend", "frontend"):
            fake.tags[f"{REGISTRY}/{service}:latest"] = PREVIOUS
        with self.assertRaisesRegex(PromotionError, "superseded draft"):
            fake.execute()
        self.assertFalse(fake.published)
        self.assertEqual(fake.calls, [])
        for service in ("backend", "frontend"):
            self.assertEqual(fake.tags[f"{REGISTRY}/{service}:latest"], PREVIOUS)

    def test_older_public_release_allows_normal_promotion(self):
        fake = FakePublisher()
        fake.published_tags = "v1.2.2"
        fake.execute()
        self.assertTrue(fake.published)
        self.assertEqual(fake.api_checks, 2)

    def test_superseding_release_appearing_during_promotion_rolls_back(self):
        fake = FakePublisher()
        fake.supersede_during_promotion = True
        for service in ("backend", "frontend"):
            fake.tags[f"{REGISTRY}/{service}:latest"] = PREVIOUS
        with self.assertRaisesRegex(PromotionError, "superseded draft"):
            fake.execute()
        self.assertFalse(fake.published)
        for service in ("backend", "frontend"):
            self.assertEqual(fake.tags[f"{REGISTRY}/{service}:latest"], PREVIOUS)

    def test_unavailable_public_releases_fail_closed(self):
        fake = FakePublisher()
        def failing_api(*args):
            raise PromotionError("GitHub releases API unavailable")
        with patch("scripts.promote_release_images.command", side_effect=failing_api):
            with self.assertRaisesRegex(PromotionError, "unavailable"):
                fake.promoter.ensure_not_superseded()

    def test_missing_backend_or_frontend_blocks_all_publication(self):
        for missing in (BACKEND, FRONTEND):
            with self.subTest(missing=missing):
                fake = FakePublisher()
                fake.sources.remove(missing)
                with self.assertRaisesRegex(PromotionError, "Missing staged"):
                    fake.execute()
                self.assertEqual(fake.calls, [])
                self.assertFalse(fake.published)

    def test_registry_failure_rolls_back_existing_aliases(self):
        fake = FakePublisher()
        for service in ("backend", "frontend"):
            fake.tags[f"{REGISTRY}/{service}:latest"] = PREVIOUS
        fake.fail_tag = (f"{REGISTRY}/frontend", "latest", FRONTEND)
        with self.assertRaisesRegex(PromotionError, "Registry push failed"):
            fake.execute()
        self.assertFalse(fake.published)
        self.assertEqual(fake.tags[f"{REGISTRY}/backend:latest"], PREVIOUS)
        self.assertEqual(fake.tags[f"{REGISTRY}/frontend:latest"], PREVIOUS)

    def test_github_release_edit_failure_restores_previous_aliases(self):
        fake = FakePublisher()
        for service in ("backend", "frontend"):
            fake.tags[f"{REGISTRY}/{service}:latest"] = PREVIOUS
        fake.fail_publish = True
        with self.assertRaisesRegex(PromotionError, "GitHub release edit failed"):
            fake.execute()
        self.assertFalse(fake.published)
        self.assertEqual(fake.tags[f"{REGISTRY}/backend:latest"], PREVIOUS)
        self.assertEqual(fake.tags[f"{REGISTRY}/frontend:latest"], PREVIOUS)

    def test_conflicting_version_tag_is_never_rewritten(self):
        fake = FakePublisher()
        fake.tags[f"{REGISTRY}/backend:1.2.3"] = PREVIOUS
        with self.assertRaisesRegex(PromotionError, "immutable"):
            fake.execute()
        self.assertEqual(fake.calls, [])
        self.assertFalse(fake.published)

    def test_retry_with_identical_digests_is_idempotent(self):
        fake = FakePublisher()
        fake.execute()
        writes = len(fake.calls)
        fake.draft, fake.published = True, False
        fake.execute()
        self.assertEqual(len(fake.calls), writes)
        self.assertTrue(fake.published)

    def test_rejects_invalid_tag_and_digest(self):
        with self.assertRaisesRegex(PromotionError, "Invalid release tag"):
            ReleasePromoter(REGISTRY, "latest", BACKEND, FRONTEND)
        with self.assertRaisesRegex(PromotionError, "Invalid image digest"):
            ReleasePromoter(REGISTRY, "v1.2.3", "not-a-digest", FRONTEND)

    def test_reads_registry_digest_from_buildx_inspect_output(self):
        from subprocess import CompletedProcess
        output = f"Name: ghcr.io/org/app:tag\nMediaType: application/vnd.oci.image.index.v1+json\nDigest: {BACKEND}\n"
        with patch(
            "scripts.promote_release_images.subprocess.run",
            return_value=CompletedProcess(["docker"], 0, output, ""),
        ):
            self.assertEqual(FakePublisher().promoter.digest_of("ghcr.io/org/app:tag"), BACKEND)

    def test_registry_copy_must_preserve_exact_digest(self):
        promoter = FakePublisher().promoter
        with patch("scripts.promote_release_images.command", side_effect=["", f"Digest: {PREVIOUS}"]):
            with self.assertRaisesRegex(PromotionError, "Digest mismatch"):
                promoter.tag_image(f"{REGISTRY}/backend", "1.2.3", BACKEND)

    def test_draft_check_rejects_published_release(self):
        promoter = FakePublisher().promoter
        with patch("scripts.promote_release_images.command", return_value="false"):
            with self.assertRaisesRegex(PromotionError, "not a draft"):
                promoter.ensure_draft()

    def test_release_recovery_rejects_non_draft_state(self):
        fake = FakePublisher()
        fake.draft = False
        with self.assertRaisesRegex(PromotionError, "Not a draft"):
            fake.execute()
        self.assertEqual(fake.calls, [])

    def test_missing_old_alias_requires_manual_recovery(self):
        import contextlib
        import io
        fake = FakePublisher()
        fake.fail_tag = (f"{REGISTRY}/frontend", "latest", FRONTEND)
        errors = io.StringIO()
        with contextlib.redirect_stderr(errors):
            with self.assertRaisesRegex(PromotionError, "Registry push failed"):
                fake.execute()
        self.assertIn("Manual alias recovery required", errors.getvalue())
        self.assertFalse(fake.published)

    def test_non_manifest_error_is_not_treated_as_missing(self):
        from subprocess import CompletedProcess
        with patch(
            "scripts.promote_release_images.subprocess.run",
            return_value=CompletedProcess(["docker"], 1, "", "unauthorized: token expired"),
        ):
            with self.assertRaisesRegex(PromotionError, "unauthorized"):
                command("docker", "buildx", "imagetools", "inspect", "ref", allow_missing=True)

    def test_missing_version_tag_is_reported_without_blocking_first_promotion(self):
        from subprocess import CompletedProcess
        with patch(
            "scripts.promote_release_images.subprocess.run",
            return_value=CompletedProcess(["docker"], 1, "", "ERROR: ghcr.io/org/app:1.2.3: not found"),
        ):
            self.assertIsNone(
                command("docker", "buildx", "imagetools", "inspect", "ref", allow_missing=True)
            )

    def test_not_found_manifest_is_missing(self):
        from subprocess import CompletedProcess
        with patch(
            "scripts.promote_release_images.subprocess.run",
            return_value=CompletedProcess(["docker"], 1, "", "manifest unknown"),
        ):
            self.assertIsNone(
                command("docker", "buildx", "imagetools", "inspect", "ref", allow_missing=True)
            )


if __name__ == "__main__":
    unittest.main()
