"""CSRFMiddleware: no client-controlled header may skip the token check."""

from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.adapters.api.middleware.csrf import CSRFMiddleware
from app.application.csrf import CSRFTokenService


@pytest.fixture
def client() -> TestClient:
    app = FastAPI()
    app.add_middleware(CSRFMiddleware, csrf_service=CSRFTokenService(secret_key="unit-test"))

    @app.post("/api/v1/things")
    async def create_thing():
        return {"created": True}

    return TestClient(app)


@pytest.mark.parametrize(
    "headers",
    [{}, {"X-API-Key": "anything"}, {"X-Api-Key": ""}],
    ids=["no-header", "api-key-header", "empty-api-key"],
)
def test_state_changing_request_without_token_is_rejected(client, headers) -> None:
    response = client.post("/api/v1/things", headers=headers)

    assert response.status_code == 403
    assert response.json()["detail"] == "CSRF validation failed"


def test_request_with_valid_token_passes(client) -> None:
    client.get("/api/v1/things")  # 405, but sets the CSRF cookie
    token = client.cookies["csrf_token"]

    response = client.post("/api/v1/things", headers={"X-CSRF-Token": token})

    assert response.json() == {"created": True}
