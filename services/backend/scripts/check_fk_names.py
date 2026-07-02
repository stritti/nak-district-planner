"""Check that FK constraint names in Alembic migrations don't exceed 63 chars.

PostgreSQL truncates identifiers longer than 63 characters, which can cause
mysterious constraint-name mismatches at runtime. This script parses migration
files with Python AST (handling multi-line calls correctly) and flags any
fk_ names that exceed the limit.
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path


def main() -> int:
    exit_code = 0
    for path in sorted(Path("alembic/versions").glob("*.py")):
        try:
            tree = ast.parse(path.read_text())
        except SyntaxError:
            continue

        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            fn = node.func
            name = None

            # op.create_foreign_key("fk_...", ...)
            if isinstance(fn, ast.Attribute) and fn.attr == "create_foreign_key" and node.args:
                arg = node.args[0]
                if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                    name = arg.value

            # op.drop_constraint("fk_...", ...)
            if isinstance(fn, ast.Attribute) and fn.attr == "drop_constraint" and node.args:
                arg = node.args[0]
                if (
                    isinstance(arg, ast.Constant)
                    and isinstance(arg.value, str)
                    and arg.value.startswith("fk_")
                ):
                    name = arg.value

            if name is not None and len(name) > 63:
                print(
                    f"❌ FK name exceeds 63 chars in {path.name}: {name} ({len(name)} chars)",
                )
                exit_code = 1

    if exit_code == 0:
        print("✅ All FK constraint names within 63-char limit")
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
