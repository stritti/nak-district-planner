"""
JWT claim enrichment for RBAC.

Extends JWT token claims with membership information for efficient
authorization checks without database queries on every request.

NOTE: We cannot modify OIDC provider tokens. Instead, this module provides
utilities to extract and validate membership claims from external sources
(if the OIDC provider supports custom claims) or to cache memberships
in a distributed cache (Redis) for fast lookups.
"""

from __future__ import annotations

import logging
import uuid
from typing import Any

from app.domain.models.membership import Membership, ScopeType
from app.domain.models.role import Role

logger = logging.getLogger(__name__)


def extract_memberships_from_claims(claims: dict[str, Any]) -> list[Membership]:
    """
    Extract membership information from JWT claims.

    This assumes the OIDC provider includes a custom claim like 'memberships'
    with the structure: [{"role": "PLANNER", "scope_type": "DISTRICT", "scope_id": "..."}]

    If the OIDC provider doesn't support custom claims, database lookup is needed
    (handled in deps.py via get_current_user_with_memberships).

    Raises invalid claims (returns empty list to fall back to DB).
    """
    memberships = []

    # Check if OIDC provider included memberships in custom claim
    if "memberships" not in claims:
        return memberships

    try:
        membership_claims = claims.get("memberships", [])
        if not isinstance(membership_claims, list):
            logger.warning(f"memberships claim is not a list: {type(membership_claims).__name__}")
            return memberships

        for idx, claim in enumerate(membership_claims):
            try:
                if not isinstance(claim, dict):
                    logger.warning(f"Membership claim {idx} is not a dict")
                    continue

                # Validate and extract fields
                role_str = claim.get("role", "")
                scope_type_str = claim.get("scope_type", "")
                scope_id_str = claim.get("scope_id", "")

                if not role_str or not scope_type_str or not scope_id_str:
                    logger.debug(f"Membership claim {idx} missing required fields")
                    continue

                # Validate enum values
                try:
                    role = Role(role_str)
                    scope_type = ScopeType(scope_type_str)
                except ValueError as e:
                    logger.warning(f"Membership claim {idx}: invalid enum value: {e}")
                    continue

                # Validate UUID
                try:
                    scope_id = uuid.UUID(str(scope_id_str))
                except (ValueError, TypeError) as e:
                    logger.warning(f"Membership claim {idx}: invalid scope_id: {e}")
                    continue

                membership = Membership(
                    id=uuid.uuid4(),
                    user_sub=claims.get("sub", ""),
                    role=role,
                    scope_type=scope_type,
                    scope_id=scope_id,
                    created_at=None,  # Not available in JWT
                    updated_at=None,  # Not available in JWT
                )
                memberships.append(membership)
            except Exception as e:
                logger.debug(f"Failed to parse membership claim {idx}: {e}")
                continue

    except Exception as e:
        logger.debug(f"Error extracting memberships from claims: {e}")

    return memberships
