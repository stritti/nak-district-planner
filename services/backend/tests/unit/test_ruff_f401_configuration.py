# SPDX-FileCopyrightText: 2026 Stephan Strittmatter
# SPDX-License-Identifier: AGPL-3.0-only

"""Regression tests for the globally enabled Ruff F401 gate and ORM re-exports."""

import subprocess
import tomllib
from pathlib import Path

import pytest

from app.adapters.db import orm_models
from app.adapters.db.base import Base

BACKEND_ROOT = Path(__file__).resolve().parents[2]


def test_global_f401_is_not_ignored() -> None:
    """The whole backend must reject unused imports, not only selected folders."""
    with (BACKEND_ROOT / "pyproject.toml").open("rb") as f:
        config = tomllib.load(f)["tool"]["ruff"]["lint"]
    assert "F" in config["select"]
    assert "F401" not in config["ignore"]


@pytest.mark.parametrize(
    ("source", "expect_success"),
    [
        ("import uuid\n\nvalue = uuid.uuid4()\n", True),
        ("import uuid\n", False),
    ],
)
def test_ruff_rejects_unused_imports_without_isolated_flags(
    tmp_path: Path, source: str, expect_success: bool
) -> None:
    """Positive and negative fixtures use the actual project configuration."""
    module = tmp_path / "f401_fixture.py"
    module.write_text(source, encoding="utf-8")
    result = subprocess.run(
        ["ruff", "check", "--config", str(BACKEND_ROOT / "pyproject.toml"), str(module)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert (result.returncode == 0) is expect_success, result.stdout + result.stderr
    if not expect_success:
        assert "F401" in result.stdout


def test_orm_imports_remain_explicit_exports_and_register_tables() -> None:
    """F401 must not remove ORM imports needed by Alembic and SQLAlchemy."""
    exports = set(orm_models.__all__)
    assert len(exports) == len(orm_models.__all__)
    assert len(exports) >= 32
    available = {
        name
        for name, model in vars(orm_models).items()
        if name.endswith("ORM") and isinstance(model, type)
    }
    assert exports == available
    for name in exports:
        model = getattr(orm_models, name)
        assert model.__table__.key in Base.metadata.tables
