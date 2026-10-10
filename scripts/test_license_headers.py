# SPDX-FileCopyrightText: 2026 Stephan Strittmatter
# SPDX-License-Identifier: AGPL-3.0-only

"""Regression tests for source license annotation and coverage."""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import license_headers as mod


class SourceSelectionTests(unittest.TestCase):
    def test_includes_backend_frontend_and_deployment(self):
        for path in (
            "services/backend/app/main.py",
            "services/backend/alembic/script.py.mako",
            "services/frontend/src/App.vue",
            "services/frontend/src/assets/main.css",
            "services/frontend/vite.config.ts",
            "docs/.vitepress/config.mts",
            "services/frontend/index.html",
            "idp-deploy/keycloak/setup_keycloak_realm.py",
            "scripts/cleanup-container-images.cjs",
            "verify-phase4b-compatibility.sh",
        ):
            with self.subTest(path=path):
                self.assertTrue(mod.is_first_party_source(path))

    def test_excludes_vendored_generated_and_non_sources(self):
        for path in (
            "third_party/ponytail/LICENSE",
            ".codex/skills/ponytail/SKILL.md",
            "services/frontend/playwright-report/index.html",
            "services/frontend/coverage/report.html",
            "services/frontend/node_modules/a/index.js",
            "services/backend/.venv/script.py",
            "services/backend/app/data.json",
            "README.md",
        ):
            with self.subTest(path=path):
                self.assertFalse(mod.is_first_party_source(path))


class HeaderTests(unittest.TestCase):
    def test_python_header_keeps_module_docstring(self):
        result = mod.annotate('"""Module."""\nfrom __future__ import annotations\n', "services/backend/app/a.py")
        self.assertTrue(mod.header_is_valid(result))
        self.assertIn('\n\n"""Module."""', result)

    def test_shell_shebang_is_first(self):
        result = mod.annotate("#!/usr/bin/env bash\nset -eu\n", "scripts/a.sh")
        self.assertTrue(result.startswith("#!/usr/bin/env bash\n# SPDX"))
        self.assertTrue(mod.header_is_valid(result))

    def test_python_shebang_and_encoding_are_first(self):
        source = "#!/usr/bin/env python3\n# coding: utf-8\nprint('ok')\n"
        result = mod.annotate(source, "scripts/a.py")
        self.assertTrue(result.startswith("#!/usr/bin/env python3\n# coding: utf-8\n# SPDX"))

    def test_vue_uses_html_comment(self):
        result = mod.annotate("<template><main/></template>\n", "services/frontend/src/App.vue")
        self.assertTrue(result.startswith("<!-- SPDX-FileCopyrightText"))
        self.assertIn("SPDX-License-Identifier: AGPL-3.0-only -->", result)

    def test_html_preserves_doctype(self):
        result = mod.annotate("<!DOCTYPE html>\n<html></html>\n", "services/frontend/index.html")
        self.assertTrue(result.startswith("<!DOCTYPE html>\n<!-- SPDX"))

    def test_css_uses_css_comment(self):
        result = mod.annotate("@import 'tailwindcss';\n", "services/frontend/src/a.css")
        self.assertTrue(result.startswith("/* SPDX-FileCopyrightText"))

    def test_typescript_uses_line_comments(self):
        result = mod.annotate("export const x = 1\n", "services/frontend/src/x.ts")
        self.assertTrue(result.startswith("// SPDX-FileCopyrightText"))

    def test_idempotent(self):
        path = "services/backend/app/x.py"
        once = mod.annotate("x=1\n", path)
        self.assertEqual(mod.annotate(once, path), once)

    def test_preserves_utf8_bom(self):
        result = mod.annotate("\ufeffx=1\n", "services/backend/app/x.py")
        self.assertTrue(result.startswith("\ufeff# SPDX"))

    def test_embedded_spdx_strings_are_not_headers(self):
        source = (
            'COPYRIGHT = "SPDX-FileCopyrightText: 2026 Stephan Strittmatter"\n'
            'LICENSE = "SPDX-License-Identifier: AGPL-3.0-only"\n'
        )
        self.assertFalse(mod.header_is_valid(source))
        annotated = mod.annotate(source, "services/backend/app/x.py")
        self.assertTrue(mod.header_is_valid(annotated))

    def test_rejects_existing_other_license(self):
        with self.assertRaises(ValueError):
            mod.annotate("# SPDX-License-Identifier: MIT\nx=1\n", "services/backend/app/x.py")

    def test_rejects_existing_copyright_for_manual_review(self):
        with self.assertRaises(ValueError):
            mod.annotate("# Copyright 2025 Other Author\n", "services/backend/app/x.py")

    def test_rejects_missing_and_multiple_identifiers(self):
        self.assertFalse(mod.header_is_valid("# SPDX-License-Identifier: AGPL-3.0-only\n"))
        valid = mod.annotate("x=1\n", "services/backend/app/x.py")
        self.assertFalse(mod.header_is_valid(valid + "# SPDX-License-Identifier: MIT\n"))
        # Header validation intentionally examines the first 16 lines only.
        self.assertFalse(mod.header_is_valid(valid.replace("AGPL-3.0-only", "MIT")))


class RepositoryTests(unittest.TestCase):
    def test_run_check_detects_missing_header(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            file = root / "services/backend/app/example.py"
            file.parent.mkdir(parents=True)
            file.write_text("x=1\n")
            with patch.object(mod, "tracked_sources", return_value=["services/backend/app/example.py"]):
                errors = mod.run(root, fix=False)
            self.assertEqual(len(errors), 1)
            self.assertEqual(file.read_text(), "x=1\n")

    def test_run_fix_and_second_check(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            file = root / "services/backend/app/example.py"
            file.parent.mkdir(parents=True)
            file.write_text("x=1\n")
            with patch.object(mod, "tracked_sources", return_value=["services/backend/app/example.py"]):
                self.assertEqual(mod.run(root, fix=True), [])
                self.assertEqual(mod.run(root, fix=False), [])
            self.assertTrue(mod.header_is_valid(file.read_text()))

    def test_run_does_not_replace_existing_third_party_attribution(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            file = root / "scripts/example.py"
            file.parent.mkdir(parents=True)
            file.write_text("# Copyright 2019 Original Author\n")
            with patch.object(mod, "tracked_sources", return_value=["scripts/example.py"]):
                errors = mod.run(root, fix=True)
            self.assertEqual(len(errors), 1)
            self.assertIn("Original Author", file.read_text())


if __name__ == "__main__":
    unittest.main()
