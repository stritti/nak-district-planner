"""Guard against the `try/except PermissionError` anti-pattern in API routers.

Routers must call `require_role_in_district()` / `require_role_in_congregation()`
(from `app.adapters.auth.permissions`), which already convert `PermissionError`
into a 403 `HTTPException`. A router that instead calls `assert_has_role_in_*()`
directly and wraps it in `except PermissionError` duplicates that conversion
logic (~48 occurrences were consolidated in the RBAC DRY refactor — see
docs/code-review-2026-07-action-plan.md PR-4). This script fails CI if a new
occurrence of the old pattern is (re-)introduced in `app/adapters/api/routers/`.

Nested/compound authorization patterns (e.g. district-OR-congregation fallback
checks in calendar_integrations.py and districts.py) are intentionally exempt
via the ALLOWLIST below — those still call `assert_has_role_in_*()` directly
because they contain business logic between the check and the raise that
`require_role_in_*()` cannot express in a single call.
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path

ROUTERS_DIR = Path("app/adapters/api/routers")

# Files where a nested/compound assert_has_role_in_* + except PermissionError
# pattern is intentionally kept (see module docstring). New files should not
# need to be added here — prefer require_role_in_district()/
# require_role_in_congregation() for any new endpoint.
ALLOWLIST = {
    "calendar_integrations.py",
    "districts.py",
}


def _is_except_permission_error(handler: ast.ExceptHandler) -> bool:
    if handler.type is None:
        return False
    if isinstance(handler.type, ast.Name):
        return handler.type.id == "PermissionError"
    return False


def main() -> int:
    exit_code = 0
    for path in sorted(ROUTERS_DIR.glob("*.py")):
        if path.name in ALLOWLIST:
            continue
        try:
            tree = ast.parse(path.read_text())
        except SyntaxError:
            continue

        for node in ast.walk(tree):
            if not isinstance(node, ast.Try):
                continue
            for handler in node.handlers:
                if _is_except_permission_error(handler):
                    print(
                        f"❌ {path}:{handler.lineno}: 'except PermissionError' found. "
                        "Use require_role_in_district()/require_role_in_congregation() "
                        "from app.adapters.auth.permissions instead (see "
                        "docs/code-review-2026-07-action-plan.md PR-4)."
                    )
                    exit_code = 1

    if exit_code == 0:
        print("✅ No 'except PermissionError' anti-pattern found in routers.")
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
