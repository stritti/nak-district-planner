"""
Authorization checks for notifications (in-app notifications UC).

When notifications are implemented, this module provides utilities to enforce
role-based permission checks for notification viewing and actions.
"""

from __future__ import annotations

import uuid

from app.adapters.auth.permissions import AuthContext
from app.domain.models.role import Role


def can_view_notification(
    auth_context: AuthContext,
    notification_district_id: uuid.UUID,
) -> bool:
    """
    Check if user can view a notification for a specific district.

    Currently, any user with VIEWER role (or higher) in the district
    can view notifications for that district.
    """
    # This will be implemented when notifications are added
    # For now, this is a placeholder for future integration
    from app.adapters.auth.permissions import has_role_in_district

    return has_role_in_district(auth_context, Role.VIEWER, notification_district_id)


def can_act_on_notification(
    auth_context: AuthContext,
    notification_district_id: uuid.UUID,
) -> bool:
    """
    Check if user can perform actions (e.g., acknowledge, close) on a notification.

    Currently requires PLANNER role (or higher) to act on notifications.
    """
    # This will be implemented when notifications are added
    # For now, this is a placeholder for future integration
    from app.adapters.auth.permissions import has_role_in_district

    return has_role_in_district(auth_context, Role.PLANNER, notification_district_id)
