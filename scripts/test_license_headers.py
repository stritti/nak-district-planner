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
            "docs/.vitepress/dist/build.js",
            "docs/.vitepress/cache/generated.mts",
            "README.md",
        ):
            with self.subTest(path=path):
                self.assertFalse(mod.is_first_party_source(path))


class HeaderTests(unittest.TestCase):
    def test_python_header_keeps_module_docstring(self):
        result = mod.annotate('"""Module."""\nfrom __future__ import annotations\n', "services/backend/app/a.py")
        self.assertTrue(mod.header_is_valid(result, "services/backend/app/a.py"))
        self.assertIn('\n\n"""Module."""', result)

    def test_shell_shebang_is_first(self):
        result = mod.annotate("#!/usr/bin/env bash\nset -eu\n", "scripts/a.sh")
        self.assertTrue(result.startswith("#!/usr/bin/env bash\n# SPDX"))
        self.assertTrue(mod.header_is_valid(result, "scripts/a.sh"))

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
        self.assertFalse(mod.header_is_valid(source, "services/backend/app/x.py"))
        annotated = mod.annotate(source, "services/backend/app/x.py")
        self.assertTrue(mod.header_is_valid(annotated, "services/backend/app/x.py"))

    def test_rejects_existing_other_license(self):
        with self.assertRaises(ValueError):
            mod.annotate("# SPDX-License-Identifier: MIT\nx=1\n", "services/backend/app/x.py")

    def test_rejects_existing_copyright_for_manual_review(self):
        with self.assertRaises(ValueError):
            mod.annotate("# Copyright 2025 Other Author\n", "services/backend/app/x.py")

    def test_rejects_missing_and_multiple_identifiers(self):
        self.assertFalse(mod.header_is_valid("# SPDX-License-Identifier: AGPL-3.0-only\n", "services/backend/app/x.py"))
        valid = mod.annotate("x=1\n", "services/backend/app/x.py")
        self.assertFalse(mod.header_is_valid(valid + "# SPDX-License-Identifier: MIT\n", "services/backend/app/x.py"))
        # Header validation intentionally examines the first 16 lines only.
        self.assertFalse(mod.header_is_valid(valid.replace("AGPL-3.0-only", "MIT"), "services/backend/app/x.py"))


class RepositoryTests(unittest.TestCase):
    def test_run_check_detects_missing_header(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            file = root / "services/backend/app/example.py"
            file.parent.mkdir(parents=True)
            file.write_text("x=1\n")
            with (
                patch.object(mod, "tracked_sources", return_value=["services/backend/app/example.py"]),
                patch.object(mod, "executable_mode_errors", return_value=[]),
            ):
                errors = mod.run(root, fix=False)
            self.assertEqual(len(errors), 1)
            self.assertEqual(file.read_text(), "x=1\n")

    def test_run_fix_and_second_check(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            file = root / "services/backend/app/example.py"
            file.parent.mkdir(parents=True)
            file.write_text("x=1\n")
            with (
                patch.object(mod, "tracked_sources", return_value=["services/backend/app/example.py"]),
                patch.object(mod, "executable_mode_errors", return_value=[]),
            ):
                self.assertEqual(mod.run(root, fix=True), [])
                self.assertEqual(mod.run(root, fix=False), [])
            self.assertTrue(mod.header_is_valid(file.read_text(), "services/backend/app/example.py"))

    def test_run_does_not_replace_existing_third_party_attribution(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            file = root / "scripts/example.py"
            file.parent.mkdir(parents=True)
            file.write_text("# Copyright 2019 Original Author\n")
            with (
                patch.object(mod, "tracked_sources", return_value=["scripts/example.py"]),
                patch.object(mod, "executable_mode_errors", return_value=[]),
            ):
                errors = mod.run(root, fix=True)
            self.assertEqual(len(errors), 1)
            self.assertIn("Original Author", file.read_text())



class ReviewRegressionTests(unittest.TestCase):
    def test_valid_header_uses_actual_comment_syntax(self):
        html = "services/frontend/index.html"
        content = "<!DOCTYPE html>\n" + mod.header_for(html) + "<html/>\n"
        self.assertTrue(mod.header_is_valid(content, html))
        self.assertFalse(mod.header_is_valid(content.replace("<!--", "#", 1), html))
        self.assertFalse(mod.header_is_valid(mod.header_for("services/backend/app/x.py"), html))
        self.assertFalse(mod.header_is_valid(mod.header_for("services/backend/app/x.py"), "services/backend/app/a.json"))

    def test_accepts_css_header_after_initial_charset(self):
        path = "services/frontend/src/index.css"
        content = '@charset "UTF-8";\nbody { color: red; }\n'
        annotated = mod.annotate(content, path)
        self.assertTrue(annotated.startswith('@charset "UTF-8";\n/* SPDX-'))
        self.assertTrue(mod.header_is_valid(annotated, path))

    def test_preserves_coding_equals_cookie(self):
        path = "services/backend/app/encoding.py"
        source = "# -*- coding=latin-1 -*-\nvalue = 'test'\n"
        annotated = mod.annotate(source, path)
        self.assertTrue(annotated.startswith("# -*- coding=latin-1 -*-\n# SPDX"))
        self.assertTrue(mod.header_is_valid(annotated, path))

    def test_preserves_second_line_encoding_cookie(self):
        path = "services/backend/app/encoding.py"
        source = "#!/usr/bin/env python3\n# coding=latin-1\nprint('hello')\n"
        annotated = mod.annotate(source, path)
        self.assertTrue(annotated.startswith("#!/usr/bin/env python3\n# coding=latin-1\n# SPDX"))
        self.assertTrue(mod.header_is_valid(annotated, path))

    def test_rejects_existing_apache_and_mit_notices(self):
        path = "services/backend/app/vendor.py"
        for notice in (
            "# Licensed under the Apache License, Version 2.0\n",
            "// License: MIT\n",
            "/* Apache License, Version 2.0 */\n",
            "# SPDX-License-Identifier: MIT\n",
            '"""Licensed under the Apache License, Version 2.0."""\n',
        ):
            with self.subTest(notice=notice):
                with self.assertRaises(ValueError):
                    mod.annotate(notice + "x = 1\n", path)

    def test_rejects_multiline_html_license_notice(self):
        path = "services/frontend/index.html"
        source = (
            "<!--\n"
            "Licensed under the Apache License,\n"
            "Version 2.0\n"
            "-->\n"
            "<!DOCTYPE html>\n<html/>\n"
        )
        with self.assertRaises(ValueError):
            mod.annotate(source, path)

    def test_rejects_multiline_css_license_notice(self):
        path = "services/frontend/src/main.css"
        source = (
            "/*\n"
            " * Copyright (c) 2025 External Author\n"
            " * MIT License\n"
            " */\nbody { color: black; }\n"
        )
        with self.assertRaises(ValueError):
            mod.annotate(source, path)

    def test_extracted_multiline_comments_are_not_code_strings(self):
        source = (
            'message = "Licensed under Apache License, Version 2.0"\n'
            "// Licensed under the MIT License\n"
            "<!--\nCopyright 2025 Example\n-->\n"
        )
        self.assertEqual(
            mod.comment_texts(source),
            [" Licensed under the MIT License", " Copyright 2025 Example"],
        )

    def test_rejects_license_docstring_after_shebang(self):
        path = "services/backend/app/vendor.py"
        source = (
            "#!/usr/bin/env python3\n"
            "# coding=utf-8\n"
            '"""Licensed under the Apache License, Version 2.0."""\n'
            "print('test')\n"
        )
        with self.assertRaises(ValueError):
            mod.annotate(source, path)

    def test_rejects_bad_header_in_other_language(self):
        html = "services/frontend/index.html"
        wrong = "# SPDX-FileCopyrightText: 2026 Stephan Strittmatter\n"
        wrong += "# SPDX-License-Identifier: AGPL-3.0-only\n\n"
        self.assertFalse(mod.header_is_valid(wrong, html))
        with self.assertRaises(ValueError):
            mod.annotate(wrong, html)

    def test_keeps_valid_source_idempotent(self):
        path = "services/frontend/src/a.vue"
        once = mod.annotate("<template><div/></template>\n", path)
        self.assertEqual(once, mod.annotate(once, path))

    def test_executable_git_modes(self):
        indexed = b"".join(
            f"100755 deadbeef 0\t{path}\0".encode("utf-8")
            for path in mod.EXECUTABLE_SCRIPTS
        )
        with patch.object(mod.subprocess, "run") as run:
            run.return_value.stdout = indexed
            self.assertEqual(mod.executable_mode_errors(Path(".")), [])

    def test_detects_non_executable_and_missing_scripts(self):
        indexed = b"100644 deadbeef 0\tscripts/backup.sh\0"
        with patch.object(mod.subprocess, "run") as run:
            run.return_value.stdout = indexed
            errors = mod.executable_mode_errors(Path("."))
        self.assertTrue(any("scripts/backup.sh" in error for error in errors))
        self.assertTrue(any("scripts/restore.sh" in error for error in errors))


if __name__ == "__main__":
    unittest.main()
