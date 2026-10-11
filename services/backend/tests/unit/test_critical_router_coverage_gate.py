# SPDX-FileCopyrightText: 2026 Stephan Strittmatter
# SPDX-License-Identifier: AGPL-3.0-only

"""Regression tests for the per-file critical-router coverage gate."""

from __future__ import annotations

import importlib.util
from pathlib import Path
from xml.etree import ElementTree

import pytest

BACKEND_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = BACKEND_ROOT / "scripts" / "check_critical_router_coverage.py"
spec = importlib.util.spec_from_file_location("critical_router_coverage", SCRIPT)
assert spec is not None and spec.loader is not None
checker = importlib.util.module_from_spec(spec)
spec.loader.exec_module(checker)


def _report(tmp_path: Path, *, rates: dict[str, float]) -> Path:
    root = ElementTree.Element("coverage")
    classes = ElementTree.SubElement(
        ElementTree.SubElement(root, "packages"), "package"
    )
    for filename, rate in rates.items():
        ElementTree.SubElement(
            ElementTree.SubElement(classes, "classes"),
            "class", {"filename": filename, "line-rate": str(rate)},
        )
    path = tmp_path / "coverage.xml"
    ElementTree.ElementTree(root).write(path, encoding="utf-8")
    return path


def test_all_critical_routers_meeting_threshold_pass(tmp_path: Path) -> None:
    xml = _report(
        tmp_path,
        rates=dict.fromkeys(checker.CRITICAL_ROUTERS, 0.8),
    )
    assert checker.check_critical_coverage(xml) == []


def test_low_coverage_fails_even_if_other_modules_are_high(tmp_path: Path) -> None:
    rates = dict.fromkeys(checker.CRITICAL_ROUTERS, 0.99)
    rates[checker.CRITICAL_ROUTERS[1]] = 0.799
    failures = checker.check_critical_coverage(
        _report(tmp_path, rates=rates)
    )
    assert len(failures) == 1
    assert "below 80%" in failures[0]


def test_missing_or_duplicated_critical_class_fails(tmp_path: Path) -> None:
    rates = dict.fromkeys(checker.CRITICAL_ROUTERS[1:], 0.95)
    missing = checker.check_critical_coverage(_report(tmp_path, rates=rates))
    assert len(missing) == 1
    assert "found 0" in missing[0]


def test_normalized_path_matches_coverage_class_filename(tmp_path: Path) -> None:
    rates = {
        "app/" + path: 0.82 for path in checker.CRITICAL_ROUTERS
    }
    assert checker.check_critical_coverage(_report(tmp_path, rates=rates)) == []


@pytest.mark.parametrize("bad_rate", [0.0, 0.5, 0.799])
def test_every_rate_below_gate_is_rejected(tmp_path: Path, bad_rate: float) -> None:
    rates = dict.fromkeys(checker.CRITICAL_ROUTERS, 1.0)
    rates[checker.CRITICAL_ROUTERS[-1]] = bad_rate
    failures = checker.check_critical_coverage(_report(tmp_path, rates=rates))
    assert len(failures) == 1
