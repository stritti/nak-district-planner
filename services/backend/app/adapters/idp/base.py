from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


class IdpProvisioningError(Exception):
    """Raised when provisioning to IDP fails."""


@dataclass(slots=True)
class IdpProvisionResult:
    status: str
    user_sub: str | None = None


class IdpProvisioner(Protocol):
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
    ) -> IdpProvisionResult: ...
