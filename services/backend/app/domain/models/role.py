from enum import Enum


class Role(str, Enum):
    """Canonical system roles for role-based access control."""

    DISTRICT_ADMIN = "DISTRICT_ADMIN"
    CONGREGATION_ADMIN = "CONGREGATION_ADMIN"
    PLANNER = "PLANNER"
    VIEWER = "VIEWER"
