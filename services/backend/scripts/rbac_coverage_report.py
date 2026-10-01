"""Print the generated endpoint inventory for docs/rbac-coverage.md.

Usage (inside services/backend/):

    uv run python scripts/rbac_coverage_report.py

The table is derived from the same analysis as
``tests/unit/test_permission_coverage.py``; paste it into the generated section
of ``docs/rbac-coverage.md`` whenever routes change.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.adapters.api.route_inventory import RouteInfo, collect_routes  # noqa: E402


def _authentication(route: RouteInfo) -> str:
    return "🔐 Auth" if route.requires_authentication else "🔓 Public"


def _guards(route: RouteInfo) -> str:
    return ", ".join(f"`{guard}`" for guard in sorted(route.guards)) or "–"


def render(routes: list[RouteInfo]) -> str:
    lines = [
        "| Methode | Pfad | Handler | Authentifizierung | Guards |",
        "|---|---|---|---|---|",
    ]
    lines += [
        f"| {', '.join(route.methods)} | `{route.path}` | `{route.key}` "
        f"| {_authentication(route)} | {_guards(route)} |"
        for route in routes
    ]
    return "\n".join(lines)


if __name__ == "__main__":
    print(render(collect_routes()))
