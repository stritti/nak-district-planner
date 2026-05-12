"""Claims validation for RBAC during request processing.

Ensures that membership claims in JWT tokens are valid and match
the system's expectations.
"""

from __future__ import annotations

from typing import Any

from app.domain.models.membership import Membership, ScopeType
from app.domain.models.role import Role


class InvalidMembershipClaimError(Exception):
    """Raised when a membership claim is invalid."""

    pass


def validate_membership_claims(claims: dict[str, Any]) -> list[Membership]:
    """Validate membership claims from JWT and return parsed Membership objects.

    Performs validation checks:
    - Membership claim structure is valid
    - Role values are recognized
    - Scope type values are recognized
    - Required fields are present

    Args:
        claims: JWT token claims dict

    Returns:
        List of valid Membership objects

    Raises:
        InvalidMembershipClaimError: If claims are invalid
    """
    memberships = []

    if "memberships" not in claims:
        # No custom membership claims (OK - will use DB lookup)
        return memberships

    membership_claims = claims.get("memberships")
    if not isinstance(membership_claims, list):
        raise InvalidMembershipClaimError(
            f"memberships claim must be a list, got {type(membership_claims).__name__}"
        )

    for idx, claim in enumerate(membership_claims):
        try:
            # Validate required fields
            if not isinstance(claim, dict):
                raise InvalidMembershipClaimError(f"Membership claim {idx} is not a dict")

            role_str = claim.get("role")
            scope_type_str = claim.get("scope_type")
            scope_id = claim.get("scope_id")

            if not role_str:
                raise InvalidMembershipClaimError(f"Membership claim {idx}: missing 'role'")
            if not scope_type_str:
                raise InvalidMembershipClaimError(f"Membership claim {idx}: missing 'scope_type'")
            if not scope_id:
                raise InvalidMembershipClaimError(f"Membership claim {idx}: missing 'scope_id'")

            # Validate enum values
            try:
                role = Role(role_str)
            except ValueError:
                raise InvalidMembershipClaimError(
                    f"Membership claim {idx}: invalid role '{role_str}'"
                )

            try:
                scope_type = ScopeType(scope_type_str)
            except ValueError:
                raise InvalidMembershipClaimError(
                    f"Membership claim {idx}: invalid scope_type '{scope_type_str}'"
                )

            # Validate scope_id is a valid UUID
            import uuid

            try:
                scope_id_uuid = uuid.UUID(str(scope_id))
            except (ValueError, TypeError):
                raise InvalidMembershipClaimError(
                    f"Membership claim {idx}: invalid scope_id '{scope_id}'"
                )

            # Create membership object (minimal info from claims)
            # Note: timestamps are not included in JWT claims
            membership = Membership(
                id=uuid.uuid4(),
                user_sub=claims.get("sub", ""),
                role=role,
                scope_type=scope_type,
                scope_id=scope_id_uuid,
                created_at=None,  # Not available in JWT
                updated_at=None,  # Not available in JWT
            )
            memberships.append(membership)

        except InvalidMembershipClaimError:
            raise
        except Exception as e:
            raise InvalidMembershipClaimError(
                f"Membership claim {idx}: validation failed: {e}"
            ) from e

    return memberships


def validate_token_claim_consistency(
    claims: dict[str, Any], db_memberships: list[Membership]
) -> bool:
    """Validate that JWT membership claims are consistent with database state.

    This check helps detect compromised or stale tokens. If a token was issued
    with certain membership claims but those memberships no longer exist in the DB,
    the token should be considered invalid or out of sync.

    NOTE: This is optional and depends on security requirements. Enabling this
    check will reject valid tokens if a user's role was recently revoked, which
    may or may not be desired behavior.

    Args:
        claims: JWT token claims
        db_memberships: Memberships from database

    Returns:
        True if claims are consistent with database, False otherwise
    """
    if "memberships" not in claims:
        # No membership claims in token, database lookup is used
        return True

    jwt_memberships = claims.get("memberships", [])

    # For consistency check, we'd need to compare:
    # - Number of memberships
    # - Role + scope combinations
    # This is a security check to detect token hijacking or role changes

    # For now, if DB has no memberships but JWT claims some, it's inconsistent
    if jwt_memberships and not db_memberships:
        return False

    # More thorough check could compare the actual membership sets
    # For MVP, we'll allow JWT claims to supplement DB data

    return True
