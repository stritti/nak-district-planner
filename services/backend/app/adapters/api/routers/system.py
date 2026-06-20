"""FastAPI router for system version and update endpoints.

Protected by RBAC — all endpoints require admin privileges.

RBAC Notes:
- /version: Requires DISTRICT_ADMIN or CONGREGATION_ADMIN role in any district
- /update: Requires SUPERADMIN role
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, Query, status

from app.adapters.api.deps import CurrentUserWithMemberships
from app.adapters.api.schemas.system import SystemVersionResponse, UpdateResponse
from app.adapters.auth.permissions import (
    get_districts_where_user_has_role,
)
from app.adapters.version_check.cache import version_cache
from app.adapters.version_check.ghcr import GhcrTagFetcher, latest_semver
from app.config import settings
from app.domain.models.role import Role

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/system", tags=["system"])


def _build_release_url(version: str) -> str:
    """Build the GitHub release URL for a given version."""
    return f"https://github.com/{settings.ghcr_owner}/{settings.ghcr_repo}/releases/tag/v{version}"


@router.get("/version", response_model=SystemVersionResponse)
async def get_version(
    auth: CurrentUserWithMemberships,
    refresh: bool = Query(False, description="Force a fresh version check"),
) -> SystemVersionResponse:
    """Return the current running version and the latest available version.

    **RBAC:** Requires DISTRICT_ADMIN or CONGREGATION_ADMIN role in any district.
    """
    # RBAC Guard: User must have DISTRICT_ADMIN or CONGREGATION_ADMIN in any district
    districts_with_admin = get_districts_where_user_has_role(
        auth, Role.DISTRICT_ADMIN
    )
    congregations_with_admin = get_districts_where_user_has_role(
        auth, Role.CONGREGATION_ADMIN
    )
    
    if not districts_with_admin and not congregations_with_admin and not auth.user.is_superadmin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Nur Administratoren (DISTRICT_ADMIN oder CONGREGATION_ADMIN) können die Version abfragen.",
        )

    current = settings.app_version

    if refresh or version_cache.get() is None:
        try:
            fetcher = GhcrTagFetcher()
            tags = fetcher.fetch_tags("backend")
            latest = latest_semver(tags)
            version_cache.set(latest)
            logger.info("Version check completed: current=%s latest=%s", current, latest)
        except Exception as e:
            logger.warning("Version check failed: %s", e)
            latest = version_cache.get()
    else:
        latest = version_cache.get()

    last_checked = version_cache.last_checked
    release_url = _build_release_url(latest) if latest else None

    return SystemVersionResponse(
        current_version=current,
        latest_version=latest,
        last_checked=last_checked,
        release_url=release_url,
    )


@router.post("/update", response_model=UpdateResponse)
async def trigger_update(
    auth: CurrentUserWithMemberships,
) -> UpdateResponse:
    """Trigger a system update.

    In manual mode: returns shell commands to run on the server.
    In docker-socket mode: fires a Celery task to pull and restart.

    **RBAC:** Requires SUPERADMIN role (highest privilege).
    """
    # RBAC Guard: Only superadmin can trigger system updates
    if not auth.user.is_superadmin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Nur Superadministratoren können das System aktualisieren.",
        )

    if settings.update_mode == "docker-socket":
        if not settings.docker_compose_dir:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=(
                    "DOCKER_COMPOSE_DIR is not configured. Set it to the project root directory."
                ),
            )
        from app.application.tasks import trigger_docker_update

        trigger_docker_update.delay()
        return UpdateResponse(status="started", mode="docker-socket")

    # Manual mode — return instructions
    return UpdateResponse(
        status="manual",
        mode="manual",
        instructions=[
            "cd /opt/nak-district-planner",
            "docker compose pull",
            "docker compose up -d",
        ],
    )
