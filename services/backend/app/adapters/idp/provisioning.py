from __future__ import annotations

from app.adapters.idp.base import IdpProvisioner, IdpProvisioningError
from app.adapters.idp.keycloak_provisioner import KeycloakProvisioningAdapter
from app.adapters.idp.webhook_provisioner import HttpIdpProvisioningAdapter
from app.config import settings


def get_idp_provisioner() -> IdpProvisioner | None:
    """Return configured provisioning adapter or None when disabled."""
    if not settings.idp_provisioning_enabled:
        return None
    if settings.idp_provisioning_provider == "keycloak":
        if (
            not settings.idp_provisioning_keycloak_base_url
            or not settings.idp_provisioning_keycloak_realm
            or not settings.idp_provisioning_keycloak_admin_username
            or not settings.idp_provisioning_keycloak_admin_password
        ):
            return None
        return KeycloakProvisioningAdapter(
            base_url=settings.idp_provisioning_keycloak_base_url,
            realm=settings.idp_provisioning_keycloak_realm,
            admin_username=settings.idp_provisioning_keycloak_admin_username,
            admin_password=settings.idp_provisioning_keycloak_admin_password,
            timeout_seconds=settings.idp_provisioning_timeout_seconds,
            invite_on_approval=settings.idp_provisioning_keycloak_invite_on_approval,
        )

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
