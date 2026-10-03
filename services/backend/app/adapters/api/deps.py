"""app/adapters/api/deps.py: Module."""

import logging
from collections.abc import Callable, Coroutine
from typing import Annotated, Any, NamedTuple, TypeVar

from fastapi import Depends, HTTPException, Request, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.auth.oidc import OIDCAdapter, TokenValidationError
from app.adapters.db.repositories.calendar_integration import SqlCalendarIntegrationRepository
from app.adapters.db.repositories.congregation import SqlCongregationRepository
from app.adapters.db.repositories.congregation_group import SqlCongregationGroupRepository
from app.adapters.db.repositories.district import SqlDistrictRepository
from app.adapters.db.repositories.district_reminder_config import (
    SqlDistrictReminderConfigRepository,
)
from app.adapters.db.repositories.event_instance import SqlEventInstanceRepository
from app.adapters.db.repositories.event_mail_hook import SqlEventMailHookRepository
from app.adapters.db.repositories.export_token import SqlExportTokenRepository
from app.adapters.db.repositories.external_event_candidate import (
    SqlExternalEventCandidateRepository,
)
from app.adapters.db.repositories.external_event_link import SqlExternalEventLinkRepository
from app.adapters.db.repositories.invitation import SqlInvitationRepository
from app.adapters.db.repositories.invitation_overwrite_request import (
    SqlInvitationOverwriteRequestRepository,
)
from app.adapters.db.repositories.leader import SqlLeaderRepository
from app.adapters.db.repositories.leader_registration import SqlLeaderRegistrationRepository
from app.adapters.db.repositories.leader_unavailability import SqlLeaderUnavailabilityRepository
from app.adapters.db.repositories.membership import SqlMembershipRepository
from app.adapters.db.repositories.notification import SqlNotificationRepository
from app.adapters.db.repositories.planning_series import SqlPlanningSeriesRepository
from app.adapters.db.repositories.planning_slot import SqlPlanningSlotRepository
from app.adapters.db.repositories.service_assignment import SqlServiceAssignmentRepository
from app.adapters.db.repositories.user import SqlUserRepository
from app.adapters.db.session import get_db_session
from app.application.candidate_review import CandidateReviewService
from app.application.notification_service import NotificationService
from app.application.services.calendar_integration_service import CalendarIntegrationService
from app.domain.models.membership import Membership
from app.domain.models.user import User

logger = logging.getLogger(__name__)

RepositoryT = TypeVar("RepositoryT")

_bearer_scheme = HTTPBearer(auto_error=False)
_oidc_adapter: OIDCAdapter | None = None


def set_oidc_adapter(adapter: OIDCAdapter | None) -> None:
    """Set the global OIDC adapter instance (called from main.py)."""
    global _oidc_adapter
    _oidc_adapter = adapter


def get_oidc_adapter() -> OIDCAdapter | None:
    """Get the currently configured global OIDC adapter instance."""
    return _oidc_adapter


async def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Security(_bearer_scheme),
    session: AsyncSession = Depends(get_db_session),
) -> User:
    """Extract and validate the current user from the bearer token."""
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Bearer token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = credentials.credentials
    if _oidc_adapter is None:
        logger.error("OIDC adapter not initialized")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Authentication service not available",
        )

    try:
        token_claims = await _oidc_adapter.validate_token(token)
        user_info = _oidc_adapter.extract_user_info(token_claims)
        user_repo = SqlUserRepository(session)
        existing_user = await user_repo.get_by_sub(user_info["sub"])

        if existing_user:
            existing_user.email = user_info["email"]
            existing_user.username = user_info["username"]
            existing_user.name = user_info["name"]
            existing_user.given_name = user_info["given_name"]
            existing_user.family_name = user_info["family_name"]
            await user_repo.save(existing_user)
        else:
            existing_user = User(
                sub=user_info["sub"],
                email=user_info["email"],
                username=user_info["username"],
                name=user_info["name"],
                given_name=user_info["given_name"],
                family_name=user_info["family_name"],
            )
            await user_repo.save(existing_user)
            logger.info("Auto-created user: %s (%s)", existing_user.sub, existing_user.email)

        try:
            await session.execute(
                text("SELECT set_config('app.current_user_sub', :user_sub, true)"),
                {"user_sub": user_info["sub"]},
            )
            result = await session.execute(
                text("SELECT grant_bootstrap_superadmin(:user_sub)"),
                {"user_sub": user_info["sub"]},
            )
            granted = bool(result.scalar_one_or_none())
        except Exception:
            logger.exception("Bootstrap superadmin reconciliation failed")
            raise

        existing_user.is_superadmin = granted
        request.state.user = existing_user
        return existing_user
    except TokenValidationError as e:
        logger.warning("Token validation failed: %s", e)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from e
    except Exception as e:
        logger.exception("Unexpected error in get_current_user")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Authentication failed",
        ) from e


class CurrentUserContext(NamedTuple):
    """User context with RBAC information."""

    user: User
    memberships: list[Membership]

    @property
    def user_sub(self) -> str:
        return self.user.sub


async def get_current_user_with_memberships(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> CurrentUserContext:
    """Get the current user together with effective memberships."""
    membership_repo = SqlMembershipRepository(session)
    memberships = await membership_repo.get_all_by_user(user.sub)

    if user.email:
        result = await session.execute(
            text(
                """
                SELECT candidate_count, granted_role, granted_scope_type, granted_scope_id
                FROM link_approved_registration(:user_sub, :email)
                """
            ),
            {"user_sub": user.sub, "email": user.email},
        )
        link_result = result.mappings().one_or_none()
        candidate_count = int(link_result["candidate_count"]) if link_result else 0
        if candidate_count == 1:
            memberships = await membership_repo.get_all_by_user(user.sub)
        elif candidate_count > 1:
            logger.warning(
                "Multiple approved unlinked registrations for email=%s; skipping auto-link",
                user.email,
            )

    from app.tenant import TenantContext

    user_roles = [membership.role.value for membership in memberships]
    if user.is_superadmin:
        user_roles.append("SUPERADMIN")
    TenantContext.set_context(
        tenant_id=TenantContext.get_tenant(),
        district_id=TenantContext.get_district(),
        congregation_id=TenantContext.get_congregation(),
        user_sub=user.sub,
        user_roles=user_roles,
    )
    await session.execute(
        text("SELECT set_config('app.current_user_sub', :user_sub, true)"),
        {"user_sub": user.sub},
    )
    await session.execute(
        text("SELECT set_config('app.current_user_roles', :roles, true)"),
        {"roles": ",".join(user_roles)},
    )

    return CurrentUserContext(user=user, memberships=memberships)


async def require_membership_access(
    auth: CurrentUserContext = Depends(get_current_user_with_memberships),
) -> CurrentUserContext:
    """Require authenticated users to have effective memberships except superadmin."""
    if auth.user.is_superadmin:
        return auth
    if not auth.memberships:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Freigabe ausstehend: kein Zugriff ohne zugewiesene Berechtigung.",
        )
    return auth


async def get_current_active_user(
    auth: CurrentUserContext = Depends(require_membership_access),
) -> User:
    """Return authenticated and approved user entity."""
    return auth.user


async def get_notification_service(
    session: AsyncSession = Depends(get_db_session),
) -> NotificationService:
    """Provide the notification service."""
    repo = SqlNotificationRepository(session)
    return NotificationService(notification_repo=repo)


def make_repository_dependency(
    repository_type: type[RepositoryT],
) -> Callable[..., Coroutine[Any, Any, RepositoryT]]:
    """Create a typed FastAPI dependency for a SQLAlchemy repository adapter."""

    async def get_repository(
        session: AsyncSession = Depends(get_db_session),
    ) -> RepositoryT:
        return repository_type(session)

    return get_repository


get_calendar_integration_repository = make_repository_dependency(SqlCalendarIntegrationRepository)
get_congregation_group_repository = make_repository_dependency(SqlCongregationGroupRepository)
get_congregation_repository = make_repository_dependency(SqlCongregationRepository)
get_district_reminder_config_repository = make_repository_dependency(
    SqlDistrictReminderConfigRepository
)
get_district_repository = make_repository_dependency(SqlDistrictRepository)
get_event_instance_repository = make_repository_dependency(SqlEventInstanceRepository)
get_event_mail_hook_repository = make_repository_dependency(SqlEventMailHookRepository)
get_export_token_repository = make_repository_dependency(SqlExportTokenRepository)
get_invitation_overwrite_request_repository = make_repository_dependency(
    SqlInvitationOverwriteRequestRepository
)
get_invitation_repository = make_repository_dependency(SqlInvitationRepository)
get_leader_registration_repository = make_repository_dependency(SqlLeaderRegistrationRepository)
get_leader_repository = make_repository_dependency(SqlLeaderRepository)
get_leader_unavailability_repository = make_repository_dependency(SqlLeaderUnavailabilityRepository)
get_membership_repository = make_repository_dependency(SqlMembershipRepository)
get_planning_series_repository = make_repository_dependency(SqlPlanningSeriesRepository)
get_planning_slot_repository = make_repository_dependency(SqlPlanningSlotRepository)
get_service_assignment_repository = make_repository_dependency(SqlServiceAssignmentRepository)
get_external_event_candidate_repository = make_repository_dependency(
    SqlExternalEventCandidateRepository
)


async def get_candidate_review_service(
    session: AsyncSession = Depends(get_db_session),
) -> CandidateReviewService:
    """Provide the candidate review service with its repository adapters."""
    return CandidateReviewService(
        candidates=SqlExternalEventCandidateRepository(session),
        slots=SqlPlanningSlotRepository(session),
        instances=SqlEventInstanceRepository(session),
        links=SqlExternalEventLinkRepository(session),
    )


async def get_calendar_integration_service(
    repository: SqlCalendarIntegrationRepository = Depends(get_calendar_integration_repository),
) -> CalendarIntegrationService:
    """Provide the calendar integration service with its repository adapter."""
    return CalendarIntegrationService(repository)


AuthenticatedUser = Annotated[User, Depends(get_current_user)]
CurrentUser = Annotated[User, Depends(get_current_active_user)]
RawCurrentUserWithMemberships = Annotated[
    CurrentUserContext, Depends(get_current_user_with_memberships)
]
CurrentUserWithMemberships = Annotated[CurrentUserContext, Depends(require_membership_access)]
CurrentActiveUser = Annotated[CurrentUserContext, Depends(require_membership_access)]
DbSession = Annotated[AsyncSession, Depends(get_db_session)]
