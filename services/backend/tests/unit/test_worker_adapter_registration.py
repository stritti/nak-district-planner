# SPDX-FileCopyrightText: 2026 Stephan Strittmatter
# SPDX-License-Identifier: AGPL-3.0-only

"""Registered Celery entrypoints belong to inbound adapter modules."""

from app.celery_app import celery


def test_celery_includes_only_adapter_task_modules() -> None:
    modules = set(celery.conf.include)
    expected = {
        "app.adapters.worker.tasks",
        "app.adapters.worker.reminder_tasks",
        "app.adapters.worker.event_mail_hook_tasks",
        "app.adapters.worker.slot_gap_tasks",
    }
    assert expected <= modules
    assert not any(path.startswith("app.application.") for path in modules)


def test_registered_task_names_remain_stable() -> None:
    from app.adapters.worker.tasks import (
        generate_planning_series_slots,
        sync_all_active_integrations,
    )

    assert generate_planning_series_slots.name == "generate_planning_series_slots"
    assert sync_all_active_integrations.name == "sync_all_active_integrations"
