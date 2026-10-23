#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Stephan Strittmatter
# SPDX-License-Identifier: AGPL-3.0-only

"""Failure-path contract tests for draft release candidate digests."""

from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.release_candidate_manifest import (
    ASSET_NAME,
    check,
    digest_pair,
    payload,
    save,
    validate,
)

TAG = "v1.2.3"
REVISION = "a" * 40
REGISTRY = "ghcr.io/stritti/nak-district-planner"
BACKEND = "sha256:" + "b" * 64
FRONTEND = "sha256:" + "c" * 64


class CandidateManifestTests(unittest.TestCase):
    def setUp(self) -> None:
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.output = Path(directory.name) / "github-output.txt"
        self.expected = payload(
            TAG, REVISION, REGISTRY, {"backend": BACKEND, "frontend": FRONTEND},
        )

    def test_both_digests_are_required(self) -> None:
        for backend, frontend in (("", FRONTEND), (BACKEND, ""), ("not-digest", FRONTEND)):
            with self.subTest(backend=backend, frontend=frontend):
                with self.assertRaisesRegex(ValueError, "Invalid candidate digest"):
                    digest_pair(backend, frontend)

    def test_validated_manifest_requires_matching_revision_and_registry(self) -> None:
        self.assertEqual(
            validate(self.expected, tag=TAG, revision=REVISION, registry=REGISTRY),
            {"backend": BACKEND, "frontend": FRONTEND},
        )
        for changed in ("tag", "revision", "registry", "schema"):
            broken = dict(self.expected)
            broken[changed] = {
                "tag": "v1.2.4",
                "revision": "f" * 40,
                "registry": "ghcr.io/other/other",
                "schema": 2,
            }[changed]
            with self.subTest(changed=changed):
                with self.assertRaises(ValueError):
                    validate(broken, tag=TAG, revision=REVISION, registry=REGISTRY)

    def test_malformed_manifest_or_missing_service_fails_closed(self) -> None:
        for corrupt in (
            {"schema": 1},
            dict(self.expected, unexpected=True),
            dict(self.expected, images={"backend": BACKEND}),
            dict(self.expected, images={"backend": FRONTEND, "frontend": "broken"}),
        ):
            with self.subTest(corrupt=corrupt):
                with self.assertRaises((ValueError, KeyError)):
                    validate(corrupt, tag=TAG, revision=REVISION, registry=REGISTRY)

    def test_no_saved_manifest_requests_original_build(self) -> None:
        with patch(
            "scripts.release_candidate_manifest.run",
            return_value=json.dumps({"assets": []}),
        ) as api:
            self.assertFalse(check(TAG, REVISION, REGISTRY, self.output))
        self.assertIn("reuse=false", self.output.read_text(encoding="utf-8"))
        self.assertNotIn("backend_digest", self.output.read_text(encoding="utf-8"))
        api.assert_called_once_with("gh", "release", "view", TAG, "--json", "assets")

    def test_saved_manifest_reuses_exact_digest_pair(self) -> None:
        def api(*args: str) -> str:
            if args[2] == "view":
                return json.dumps({"assets": [{"name": ASSET_NAME}]})
            if args[2] == "download":
                (Path(args[-1]) / ASSET_NAME).write_text(
                    json.dumps(self.expected), encoding="utf-8",
                )
                return ""
            raise AssertionError(f"Unexpected command: {args}")

        with patch("scripts.release_candidate_manifest.run", side_effect=api):
            self.assertTrue(check(TAG, REVISION, REGISTRY, self.output))
        contents = self.output.read_text(encoding="utf-8")
        self.assertIn("reuse=true", contents)
        self.assertIn(f"backend_digest={BACKEND}", contents)
        self.assertIn(f"frontend_digest={FRONTEND}", contents)

    def test_untrusted_or_wrong_version_asset_does_not_rebuild(self) -> None:
        bad = dict(self.expected, revision="f" * 40)

        def api(*args: str) -> str:
            if args[2] == "view":
                return json.dumps({"assets": [{"name": ASSET_NAME}]})
            if args[2] == "download":
                (Path(args[-1]) / ASSET_NAME).write_text(json.dumps(bad), encoding="utf-8")
                return ""
            raise AssertionError(f"Unexpected command: {args}")

        with patch("scripts.release_candidate_manifest.run", side_effect=api):
            with self.assertRaisesRegex(ValueError, "does not match"):
                check(TAG, REVISION, REGISTRY, self.output)
        self.assertFalse(self.output.exists())

    def test_registry_or_github_failure_is_not_treated_as_missing_asset(self) -> None:
        with patch(
            "scripts.release_candidate_manifest.run",
            side_effect=subprocess.CalledProcessError(1, ["gh", "release", "view"]),
        ):
            with self.assertRaises(subprocess.CalledProcessError):
                check(TAG, REVISION, REGISTRY, self.output)
        self.assertFalse(self.output.exists())

    def test_upload_persists_pair_before_exposing_outputs(self) -> None:
        uploaded = {}

        def api(*args: str) -> str:
            uploaded.update(json.loads(Path(args[4]).read_text(encoding="utf-8")))
            return ""

        with patch("scripts.release_candidate_manifest.run", side_effect=api) as gh:
            save(TAG, REVISION, REGISTRY, self.output, BACKEND, FRONTEND)
        gh.assert_called_once()
        self.assertEqual(uploaded, self.expected)
        self.assertIn(f"backend_digest={BACKEND}", self.output.read_text(encoding="utf-8"))
        self.assertIn(f"frontend_digest={FRONTEND}", self.output.read_text(encoding="utf-8"))

    def test_upload_failure_never_exposes_a_digest_pair(self) -> None:
        with patch(
            "scripts.release_candidate_manifest.run",
            side_effect=subprocess.CalledProcessError(1, ["gh", "release", "upload"]),
        ):
            with self.assertRaises(subprocess.CalledProcessError):
                save(TAG, REVISION, REGISTRY, self.output, BACKEND, FRONTEND)
        self.assertFalse(self.output.exists())


if __name__ == "__main__":
    unittest.main()
