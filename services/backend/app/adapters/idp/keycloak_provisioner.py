"""app/adapters/idp/keycloak_provisioner.py: Module."""

from __future__ import annotations

import re
from typing import Any

import httpx

from app.adapters.idp.base import IdpProvisionResult, IdpProvisioner, IdpProvisioningError


class KeycloakProvisioningAdapter(IdpProvisioner):
    """Direct provisioning against Keycloak Admin API."""

    def __init__(
        self,
        *,
        base_url: str,
        realm: str,
        admin_username: str,
        admin_password: str,
        timeout_seconds: float,
        invite_on_approval: bool,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._realm = realm
        self._admin_username = admin_username
        self._admin_password = admin_password
        self._timeout_seconds = timeout_seconds
        self._invite_on_approval = invite_on_approval

    async def _get_admin_token(self) -> str:
        token_url = f"{self._base_url}/realms/master/protocol/openid-connect/token"
        data = {
            "grant_type": "password",
            "client_id": "admin-cli",
            "username": self._admin_username,
            "password": self._admin_password,
        }
        try:
            async with httpx.AsyncClient(timeout=self._timeout_seconds) as client:
                response = await client.post(token_url, data=data)
        except httpx.HTTPError as exc:
            raise IdpProvisioningError("Keycloak admin token request failed") from exc
        if response.status_code >= 400:
            raise IdpProvisioningError(
                f"Keycloak admin token request failed: {response.status_code} {response.text}"
            )
        try:
            payload = response.json()
        except ValueError as exc:
            raise IdpProvisioningError("Keycloak token response is not valid JSON") from exc
        token = payload.get("access_token") if isinstance(payload, dict) else None
        if not isinstance(token, str) or not token:
            raise IdpProvisioningError("Keycloak token response missing access_token")
        return token

    async def _find_user_by_email(self, *, token: str, email: str) -> dict[str, Any] | None:
        users_url = f"{self._base_url}/admin/realms/{self._realm}/users"
        headers = {"Authorization": f"Bearer {token}"}
        params = {"email": email, "exact": "true"}
        try:
            async with httpx.AsyncClient(timeout=self._timeout_seconds) as client:
                response = await client.get(users_url, headers=headers, params=params)
        except httpx.HTTPError as exc:
            raise IdpProvisioningError("Keycloak user lookup failed") from exc
        if response.status_code >= 400:
            raise IdpProvisioningError(
                f"Keycloak user lookup failed: {response.status_code} {response.text}"
            )
        try:
            payload = response.json()
        except ValueError as exc:
            raise IdpProvisioningError("Keycloak user lookup returned invalid JSON") from exc
        if not isinstance(payload, list):
            raise IdpProvisioningError("Keycloak user lookup returned unexpected shape")
        for entry in payload:
            if isinstance(entry, dict) and isinstance(entry.get("id"), str):
                return entry
        return None

    async def _create_user(self, *, token: str, email: str, name: str) -> str:
        users_url = f"{self._base_url}/admin/realms/{self._realm}/users"
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }
        first_name, last_name = self._split_name(name)
        payload: dict[str, Any] = {
            "username": email,
            "email": email,
            "enabled": True,
            "emailVerified": False,
        }
        if first_name:
            payload["firstName"] = first_name
        if last_name:
            payload["lastName"] = last_name

        try:
            async with httpx.AsyncClient(timeout=self._timeout_seconds) as client:
                response = await client.post(users_url, headers=headers, json=payload)
        except httpx.HTTPError as exc:
            raise IdpProvisioningError("Keycloak user creation failed") from exc

        if response.status_code not in (201, 409):
            raise IdpProvisioningError(
                f"Keycloak user creation failed: {response.status_code} {response.text}"
            )

        if response.status_code == 409:
            existing = await self._find_user_by_email(token=token, email=email)
            if existing and isinstance(existing.get("id"), str):
                return existing["id"]
            raise IdpProvisioningError("Keycloak returned 409 but user lookup by email failed")

        location = response.headers.get("Location")
        if location:
            user_id = location.rstrip("/").rsplit("/", 1)[-1]
            if user_id:
                return user_id

        existing = await self._find_user_by_email(token=token, email=email)
        if existing and isinstance(existing.get("id"), str):
            return existing["id"]
        raise IdpProvisioningError("Keycloak user created but id could not be resolved")

    async def _trigger_invite(self, *, token: str, user_id: str) -> None:
        actions_url = (
            f"{self._base_url}/admin/realms/{self._realm}/users/{user_id}/execute-actions-email"
        )
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }
        required_actions = ["VERIFY_EMAIL", "UPDATE_PASSWORD"]
        try:
            async with httpx.AsyncClient(timeout=self._timeout_seconds) as client:
                response = await client.put(actions_url, headers=headers, json=required_actions)
        except httpx.HTTPError as exc:
            raise IdpProvisioningError("Keycloak invite email failed") from exc
        if response.status_code >= 400:
            raise IdpProvisioningError(
                f"Keycloak invite email failed: {response.status_code} {response.text}"
            )

    @staticmethod
    def _split_name(name: str) -> tuple[str | None, str | None]:
        trimmed = name.strip()
        if not trimmed:
            return None, None
        parts = re.split(r"\s+", trimmed)
        if len(parts) == 1:
            return parts[0], None
        return parts[0], " ".join(parts[1:])

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
        del district_id, registration_id, role, scope_type, scope_id
        token = await self._get_admin_token()
        existing = await self._find_user_by_email(token=token, email=email)
        created = False
        if existing is not None:
            user_id = str(existing["id"])
        else:
            user_id = await self._create_user(token=token, email=email, name=name)
            created = True

        if self._invite_on_approval:
            await self._trigger_invite(token=token, user_id=user_id)

        if created and self._invite_on_approval:
            status = "CREATED_INVITED"
        elif created:
            status = "CREATED"
        elif self._invite_on_approval:
            status = "EXISTING_INVITED"
        else:
            status = "EXISTING"
        return IdpProvisionResult(status=status, user_sub=user_id)
