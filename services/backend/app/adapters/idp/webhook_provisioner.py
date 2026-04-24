"""app/adapters/idp/webhook_provisioner.py: Module."""

from __future__ import annotations

from typing import Any

import httpx

from app.adapters.idp.base import IdpProvisioner, IdpProvisioningError, IdpProvisionResult


class HttpIdpProvisioningAdapter(IdpProvisioner):
    """Provider-agnostic HTTP adapter for IDP provisioning/invite automation."""

    def __init__(
        self,
        endpoint: str,
        api_key: str | None,
        timeout_seconds: float,
    ) -> None:
        self._endpoint = endpoint
        self._api_key = api_key
        self._timeout_seconds = timeout_seconds

    async def provision_user(
        self,
        *,
        email: str,
        name: str,
        district_id: str,
        registration_id: str,
        role: str,
        scope_type: str,
        scope_id: str,
    ) -> IdpProvisionResult:
        headers: dict[str, str] = {
            "Content-Type": "application/json",
        }
        if self._api_key:
            headers["Authorization"] = f"Bearer {self._api_key}"

        payload = {
            "email": email,
            "name": name,
            "district_id": district_id,
            "registration_id": registration_id,
            "role": role,
            "scope_type": scope_type,
            "scope_id": scope_id,
        }

        try:
            async with httpx.AsyncClient(timeout=self._timeout_seconds) as client:
                response = await client.post(self._endpoint, json=payload, headers=headers)
        except httpx.HTTPError as exc:
            raise IdpProvisioningError(f"Provisioning request failed: {exc}") from exc

        if response.status_code >= 400:
            raise IdpProvisioningError(
                f"Provisioning endpoint returned {response.status_code}: {response.text}"
            )

        body: Any
        try:
            body = response.json()
        except ValueError as exc:
            raise IdpProvisioningError("Provisioning endpoint returned invalid JSON") from exc

        if not isinstance(body, dict):
            raise IdpProvisioningError("Provisioning endpoint returned invalid payload shape")

        status_value = body.get("status")
        if not isinstance(status_value, str) or not status_value.strip():
            raise IdpProvisioningError("Provisioning response missing required field 'status'")

        user_sub = body.get("user_sub")
        if user_sub is not None and not isinstance(user_sub, str):
            raise IdpProvisioningError("Provisioning response field 'user_sub' has invalid type")

        return IdpProvisionResult(status=status_value, user_sub=user_sub)
