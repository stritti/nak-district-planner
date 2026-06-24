"""app/domain/models/role.py: Module."""

from enum import Enum, StrEnum


class Role(StrEnum):
    """Canonical system roles for role-based access control.
    
    Roles are ordered from highest to lowest privilege.
    Numeric values are used for comparison to ensure correct hierarchy.
    """

    DISTRICT_ADMIN = "DISTRICT_ADMIN"
    CONGREGATION_ADMIN = "CONGREGATION_ADMIN"
    PLANNER = "PLANNER"
    VIEWER = "VIEWER"
    
    def __lt__(self, other: "Role") -> bool:
        """Compare roles by privilege level (higher privilege > lower privilege).
        
        Returns True if self has LOWER privilege than other.
        """
        # Define the hierarchy order from highest to lowest
        hierarchy = [Role.DISTRICT_ADMIN, Role.CONGREGATION_ADMIN, Role.PLANNER, Role.VIEWER]
        # Lower index = higher privilege, so self < other means self has lower privilege
        return hierarchy.index(self) > hierarchy.index(other)
    
    def __le__(self, other: "Role") -> bool:
        return self < other or self == other
    
    def __gt__(self, other: "Role") -> bool:
        return other < self
    
    def __ge__(self, other: "Role") -> bool:
        return other <= self
