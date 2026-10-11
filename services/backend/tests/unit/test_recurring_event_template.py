# SPDX-FileCopyrightText: 2026 Stephan Strittmatter
# SPDX-License-Identifier: AGPL-3.0-only

"""Regression tests for recurring events before any persistence/API integration."""

from __future__ import annotations

import uuid
from dataclasses import replace
from datetime import UTC, date, datetime, time, timedelta

import pytest

from app.domain.models.recurring_event_template import (
    AmbiguousLocalTimeError,
    DecisionStatus,
    NonexistentLocalTimeError,
    RecurrenceKind,
    RecurrenceRule,
    RecurringEventDecision,
    RecurringEventTemplate,
    expand_month,
    local_start_utc,
    utc_interval,
)


def rule(kind: RecurrenceKind, anchor: date = date(2026, 9, 1), **options) -> RecurrenceRule:
    return RecurrenceRule(kind=kind, anchor_date=anchor, **options)


def template(recurrence: RecurrenceRule, **overrides) -> RecurringEventTemplate:
    params = {
        "id": uuid.uuid4(),
        "district_id": uuid.uuid4(),
        "title": "Chorprobe",
        "category": "Musik",
        "start_time": time(19, 30),
        "duration_minutes": 90,
        "recurrence": recurrence,
    }
    params.update(overrides)
    return RecurringEventTemplate(**params)


def test_every_tuesday_and_anchor_stable_across_separate_month_queries() -> None:
    entry = template(rule(RecurrenceKind.WEEKLY, weekdays=(2,)))
    assert expand_month(entry, 2026, 10) == [
        date(2026, 10, 6),
        date(2026, 10, 13),
        date(2026, 10, 20),
        date(2026, 10, 27),
    ]
    assert expand_month(entry, 2026, 9) == [
        date(2026, 9, 1),
        date(2026, 9, 8),
        date(2026, 9, 15),
        date(2026, 9, 22),
        date(2026, 9, 29),
    ]


def test_biweekly_interval_uses_anchor_not_start_of_viewed_month() -> None:
    entry = template(rule(RecurrenceKind.WEEKLY, weekdays=(2,), interval=2))
    assert expand_month(entry, 2026, 10) == [date(2026, 10, 13), date(2026, 10, 27)]
    assert expand_month(entry, 2026, 8) == []


@pytest.mark.parametrize(
    ("ordinal", "weekday", "month", "expected"),
    [
        (-1, 2, 10, [date(2026, 10, 27)]),
        (1, 2, 10, [date(2026, 10, 6)]),
        (5, 2, 10, []),
        (5, 4, 10, [date(2026, 10, 29)]),
    ],
)
def test_nth_and_last_weekday(ordinal, weekday, month, expected) -> None:
    entry = template(
        rule(RecurrenceKind.MONTHLY_WEEKDAY, weekday=weekday, ordinal=ordinal)
    )
    assert expand_month(entry, 2026, month) == expected


def test_monthly_missing_dates_and_leap_year() -> None:
    monthly = template(
        rule(RecurrenceKind.MONTHLY_DAY, date(2028, 1, 1), day_of_month=29)
    )
    assert expand_month(monthly, 2028, 2) == [date(2028, 2, 29)]
    assert expand_month(monthly, 2029, 2) == []
    monthly_31 = replace(
        monthly, recurrence=rule(RecurrenceKind.MONTHLY_DAY, day_of_month=31)
    )
    assert expand_month(monthly_31, 2026, 4) == []
    assert expand_month(monthly_31, 2026, 10) == [date(2026, 10, 31)]


def test_monthly_anchor_day_and_year_boundary() -> None:
    entry = template(
        rule(
            RecurrenceKind.MONTHLY_DAY, date(2026, 11, 20),
            day_of_month=10, interval=2
        )
    )
    assert expand_month(entry, 2026, 11) == []
    assert expand_month(entry, 2026, 12) == []
    assert expand_month(entry, 2027, 1) == [date(2027, 1, 10)]
    assert expand_month(entry, 2027, 2) == []


def test_active_bounds_inclusive_and_inactive_template() -> None:
    entry = template(
        rule(RecurrenceKind.WEEKLY, weekdays=(2,)),
        active_from=date(2026, 10, 13),
        active_until=date(2026, 10, 20),
    )
    assert expand_month(entry, 2026, 10) == [date(2026, 10, 13), date(2026, 10, 20)]
    assert expand_month(replace(entry, is_active=False), 2026, 10) == []


def test_weekdays_are_sorted_and_not_silently_deduplicated() -> None:
    weekly = rule(RecurrenceKind.WEEKLY, weekdays=(5, 1))
    assert weekly.weekdays == (1, 5)
    with pytest.raises(ValueError, match="Invalid weekly"):
        rule(RecurrenceKind.WEEKLY, weekdays=(2, 2))


@pytest.mark.parametrize(
    ("kind", "kwargs"),
    [
        (RecurrenceKind.WEEKLY, {"weekdays": ()}),
        (RecurrenceKind.WEEKLY, {"weekdays": (0,)}),
        (RecurrenceKind.WEEKLY, {"weekdays": (True,)}),
        (RecurrenceKind.WEEKLY, {"day_of_month": 5, "weekdays": (2,)}),
        (RecurrenceKind.MONTHLY_DAY, {"day_of_month": 0}),
        (RecurrenceKind.MONTHLY_DAY, {"day_of_month": 32}),
        (RecurrenceKind.MONTHLY_DAY, {"day_of_month": 1, "weekday": 2}),
        (RecurrenceKind.MONTHLY_WEEKDAY, {"weekday": 8, "ordinal": 1}),
        (RecurrenceKind.MONTHLY_WEEKDAY, {"weekday": 2, "ordinal": 0}),
        (RecurrenceKind.MONTHLY_WEEKDAY, {"weekday": 2, "ordinal": 6}),
    ],
)
def test_invalid_pattern_rejected(kind, kwargs) -> None:
    with pytest.raises(ValueError):
        rule(kind, **kwargs)


def test_bad_anchor_interval_version_and_requested_month_rejected() -> None:
    for overrides in (
        {"interval": 0, "weekdays": (2,)},
        {"interval": True, "weekdays": (2,)},
        {"version": 2, "weekdays": (2,)},
    ):
        with pytest.raises(ValueError):
            rule(RecurrenceKind.WEEKLY, **overrides)
    with pytest.raises(ValueError):
        RecurrenceRule(
            kind=RecurrenceKind.WEEKLY, anchor_date=datetime(2026, 9, 1), weekdays=(2,)
        )
    with pytest.raises(ValueError):
        RecurrenceRule(kind="YEARLY", anchor_date=date(2026, 9, 1))
    with pytest.raises(ValueError):
        expand_month(template(rule(RecurrenceKind.WEEKLY, weekdays=(2,))), 2026, 13)


@pytest.mark.parametrize(
    "overrides",
    [
        {"title": " "},
        {"category": ""},
        {"category": "Gottesdienst"},
        {"category": "gOtTeSdIeNsT"},
        {"duration_minutes": 0},
        {"revision": 0},
        {"timezone": "UTC"},
        {"start_time": time(10, tzinfo=UTC)},
        {"active_from": date(2026, 10, 2), "active_until": date(2026, 10, 1)},
        {"applicability": ("all", str(uuid.uuid4()))},
        {"applicability": ("invalid",)},
        {"applicability": ("all", "all")},
        {"congregation_id": uuid.uuid4(), "applicability": ("all",)},
    ],
)
def test_template_rejects_invalid_identity_scope_and_service(overrides) -> None:
    with pytest.raises(ValueError):
        template(rule(RecurrenceKind.WEEKLY, weekdays=(2,)), **overrides)


def test_valid_district_applicability_and_congregation_template() -> None:
    event = template(
        rule(RecurrenceKind.WEEKLY, weekdays=(2,)),
        applicability=(str(uuid.uuid4()),),
    )
    assert event.applicability
    assert not replace(event, congregation_id=None, applicability=()).applicability
    congregation = template(
        rule(RecurrenceKind.WEEKLY, weekdays=(2,)),
        congregation_id=uuid.uuid4(),
    )
    assert congregation.congregation_id is not None


def test_normal_winter_and_summer_clock_times_remain_local_1930() -> None:
    winter = local_start_utc(date(2026, 1, 6), time(19, 30))
    summer = local_start_utc(date(2026, 7, 7), time(19, 30))
    assert winter == datetime(2026, 1, 6, 18, 30, tzinfo=UTC)
    assert summer == datetime(2026, 7, 7, 17, 30, tzinfo=UTC)


def test_dst_spring_gap_fails_instead_of_shifting_clock() -> None:
    with pytest.raises(NonexistentLocalTimeError):
        local_start_utc(date(2026, 3, 29), time(2, 30))


def test_dst_fall_fold_requires_explicit_choice() -> None:
    with pytest.raises(AmbiguousLocalTimeError):
        local_start_utc(date(2026, 10, 25), time(2, 30))
    assert local_start_utc(date(2026, 10, 25), time(2, 30), fold=0) == datetime(
        2026, 10, 25, 0, 30, tzinfo=UTC
    )
    assert local_start_utc(date(2026, 10, 25), time(2, 30), fold=1) == datetime(
        2026, 10, 25, 1, 30, tzinfo=UTC
    )


def test_bad_fold_and_timezone_rejected() -> None:
    with pytest.raises(ValueError):
        local_start_utc(date(2026, 7, 1), time(12), fold=2)
    with pytest.raises(ValueError):
        local_start_utc(date(2026, 7, 1), time(12), fold=True)
    with pytest.raises(ValueError):
        local_start_utc(date(2026, 7, 1), time(12), fold=1)
    with pytest.raises(ValueError):
        local_start_utc(date(2026, 7, 1), time(12), timezone="UTC")
    with pytest.raises(ValueError):
        local_start_utc(date(2026, 7, 1), time(12, tzinfo=UTC))


def test_event_duration_is_elapsed_time_in_utc() -> None:
    entry = template(
        rule(RecurrenceKind.MONTHLY_DAY, day_of_month=29),
        start_time=time(1, 30),
        duration_minutes=120,
    )
    start, end = utc_interval(entry, date(2026, 3, 29))
    assert end - start == timedelta(hours=2)
    assert start == datetime(2026, 3, 29, 0, 30, tzinfo=UTC)


def test_decisions_keep_occurrence_identity_when_slot_is_later_moved() -> None:
    identifier = uuid.uuid4()
    selected = date(2026, 10, 27)
    accepted = RecurringEventDecision(
        id=uuid.uuid4(),
        district_id=uuid.uuid4(),
        template_id=identifier,
        occurrence_local_date=selected,
        status=DecisionStatus.ACCEPTED,
        created_by="user-sub",
        planning_slot_id=uuid.uuid4(),
    )
    assert accepted.occurrence_key == (identifier, selected)
    assert replace(accepted, planning_slot_id=None).occurrence_key == (identifier, selected)
    with pytest.raises(ValueError):
        replace(accepted, status=DecisionStatus.SKIPPED)
