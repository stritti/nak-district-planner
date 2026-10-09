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
