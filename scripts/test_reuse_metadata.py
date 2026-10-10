# SPDX-FileCopyrightText: 2026 Stephan Strittmatter
# SPDX-License-Identifier: AGPL-3.0-only

"""REUSE configuration invariants; reuse lint provides full coverage checks."""

from __future__ import annotations

import tomllib
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class ReuseMetadataTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.configuration = tomllib.loads((ROOT / "REUSE.toml").read_text(encoding="utf-8"))

    def test_schema_and_fallback(self) -> None:
        self.assertEqual(self.configuration["version"], 1)
        default = self.configuration["annotations"][0]
        self.assertEqual(default["path"], "**")
        self.assertEqual(default["precedence"], "closest")
        self.assertEqual(default["SPDX-License-Identifier"], "AGPL-3.0-only")

    def test_third_party_overrides_preserved(self) -> None:
        overrides = [
            annotation for annotation in self.configuration["annotations"]
            if annotation.get("precedence") == "override"
        ]
        self.assertGreaterEqual(len(overrides), 3)
        self.assertTrue(all(a["SPDX-License-Identifier"] == "MIT" for a in overrides))
        self.assertTrue(any(
            "third_party/ponytail/**" in annotation["path"]
            and annotation["SPDX-FileCopyrightText"] == "2026 DietrichGebert"
            for annotation in overrides
        ))
        self.assertTrue(any(
            ".agent/skills/openspec-*/**" in annotation["path"]
            for annotation in overrides
        ))

    def test_agpl_text_matches_main_license(self) -> None:
        self.assertEqual(
            (ROOT / "LICENSES/AGPL-3.0-only.txt").read_bytes(),
            (ROOT / "LICENSE").read_bytes(),
        )

    def test_mit_text_preserves_original_third_party_notice(self) -> None:
        self.assertEqual(
            (ROOT / "LICENSES/MIT.txt").read_bytes(),
            (ROOT / "third_party/ponytail/LICENSE").read_bytes(),
        )

    def test_literal_spdx_example_files_are_not_misinterpreted(self) -> None:
        last = self.configuration["annotations"][-1]
        self.assertEqual(last["precedence"], "override")
        self.assertEqual(last["SPDX-License-Identifier"], "AGPL-3.0-only")
        self.assertIn("scripts/test_license_headers.py", last["path"])
        self.assertIn("docs/engineering-standards.md", last["path"])

    def test_license_files_only_for_actual_licenses(self) -> None:
        self.assertEqual(
            {p.name for p in (ROOT / "LICENSES").iterdir()},
            {"AGPL-3.0-only.txt", "MIT.txt"},
        )


if __name__ == "__main__":
    unittest.main()
