# SPDX-FileCopyrightText: 2026 Stephan Strittmatter
# SPDX-License-Identifier: AGPL-3.0-only

"""app/adapters/idp/provisioning.py: Module."""

from __future__ import annotations

from app.adapters.idp.base import IdpProvisioner, IdpProvisioningError
from app.adapters.idp.webhook_provisioner import HttpIdpProvisioningAdapter
from app.config import settings


def get_idp_provisioner() -> IdpProvisioner | None:
    """Return configured provisioning adapter or None when disabled."""
    if not settings.idp_provisioning_enabled:
        return None
    if settings.idp_provisioning_provider == "webhook":
        if not settings.idp_provisioning_endpoint:
            return None
        return HttpIdpProvisioningAdapter(
            endpoint=settings.idp_provisioning_endpoint,
            api_key=settings.idp_provisioning_api_key,
            timeout_seconds=settings.idp_provisioning_timeout_seconds,
        )
    return None


__all__ = ["IdpProvisioningError", "get_idp_provisioner"]
