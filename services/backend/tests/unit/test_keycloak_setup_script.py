# SPDX-FileCopyrightText: 2026 Stephan Strittmatter
# SPDX-License-Identifier: AGPL-3.0-only

"""idp-deploy/keycloak/setup_keycloak_realm.py: the client needs an audience mapper."""

from __future__ import annotations

import importlib.util
from pathlib import Path
from unittest.mock import MagicMock, patch

SCRIPT = Path(__file__).parents[4] / "idp-deploy" / "keycloak" / "setup_keycloak_realm.py"


def _load():
    spec = importlib.util.spec_from_file_location("setup_keycloak_realm", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _admin(module):
    admin = module.KeycloakAdminClient.__new__(module.KeycloakAdminClient)
    admin.keycloak_url = "http://kc"
    admin._headers = lambda: {}
    return admin


def _response(status: int = 200, body=None) -> MagicMock:
    response = MagicMock(status_code=status, text="")
    response.json.return_value = body if body is not None else []
    return response


def test_audience_mapper_payload_adds_client_id_to_access_token() -> None:
    module = _load()
    with (
        patch.object(module.requests, "get", return_value=_response(200, [])),
        patch.object(module.requests, "post", return_value=_response(201)) as post,
    ):
        _admin(module).ensure_audience_mapper("nak-planner", "uuid-1", "nak-planner-frontend")

    url = post.call_args.args[0]
    payload = post.call_args.kwargs["json"]
    assert url == "http://kc/admin/realms/nak-planner/clients/uuid-1/protocol-mappers/models"
    assert payload["protocolMapper"] == "oidc-audience-mapper"
    assert payload["config"]["included.client.audience"] == "nak-planner-frontend"
    assert payload["config"]["access.token.claim"] == "true"


def test_audience_mapper_is_idempotent() -> None:
    module = _load()
    existing = [{"name": module.KeycloakAdminClient.AUDIENCE_MAPPER_NAME}]
    with (
        patch.object(module.requests, "get", return_value=_response(200, existing)),
        patch.object(module.requests, "post") as post,
    ):
        _admin(module).ensure_audience_mapper("nak-planner", "uuid-1", "nak-planner-frontend")

    post.assert_not_called()


def test_realm_security_defaults_payload() -> None:
    module = _load()
    with patch.object(module.requests, "put", return_value=_response(204)) as put:
        _admin(module).apply_realm_security_defaults("nak-planner")

    assert put.call_args.args[0] == "http://kc/admin/realms/nak-planner"
    payload = put.call_args.kwargs["json"]
    assert payload["registrationAllowed"] is False
    assert payload["verifyEmail"] is True
    assert payload["bruteForceProtected"] is True
    assert "length(12)" in payload["passwordPolicy"]


def test_provisioning_client_is_confidential_service_account_with_minimal_roles() -> None:
    module = _load()

    def fake_get(url, **_kwargs):
        if url.endswith("clientId=nak-planner-provisioning"):
            return _response(200, [{"id": "prov-uuid"}])
        if url.endswith("clientId=realm-management"):
            return _response(200, [{"id": "rm-uuid"}])
        if url.endswith("/service-account-user"):
            return _response(200, {"id": "sa-user"})
        if url.endswith("/client-secret"):
            return _response(200, {"value": "generated-secret"})
        role = url.rsplit("/", 1)[-1]
        return _response(200, {"id": f"{role}-id", "name": role})

    with (
        patch.object(module.requests, "get", side_effect=fake_get),
        patch.object(module.requests, "post", side_effect=[_response(201), _response(204)]) as post,
    ):
        secret = _admin(module).ensure_provisioning_client(
            "nak-planner", "nak-planner-provisioning"
        )

    assert secret == "generated-secret"
    client_payload = post.call_args_list[0].kwargs["json"]
    assert client_payload["publicClient"] is False
    assert client_payload["serviceAccountsEnabled"] is True
    assert client_payload["standardFlowEnabled"] is False
    assert client_payload["directAccessGrantsEnabled"] is False
    mapping = post.call_args_list[1]
    assert mapping.args[0] == (
        "http://kc/admin/realms/nak-planner/users/sa-user/role-mappings/clients/rm-uuid"
    )
    assert [r["name"] for r in mapping.kwargs["json"]] == ["manage-users", "view-users"]
