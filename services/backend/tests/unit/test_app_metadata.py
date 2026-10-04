"""Regression tests for application metadata exposed by FastAPI."""

from app.config import settings
from app.main import app


def test_fastapi_version_uses_central_application_version() -> None:
    assert app.version == settings.app_version
