# SPDX-FileCopyrightText: 2026 Stephan Strittmatter
# SPDX-License-Identifier: AGPL-3.0-only

"""Leader assignments in the domain model (step 4)."""

from __future__ import annotations

import uuid

from app.domain.models.leader import Leader, LeaderAssignment, SpecialRole

DISTRICT, CONGREGATION = uuid.uuid4(), uuid.uuid4()


def test_a_new_leader_has_exactly_one_home_assignment() -> None:
    leader = Leader.create(
        name="Hans", district_id=DISTRICT, congregation_id=CONGREGATION,
        special_role=SpecialRole.GEMEINDEVORSTEHER,
    )
    [home] = leader.assignments
    assert home.is_home and home.leader_id == leader.id and home.district_id == DISTRICT
    assert (home.congregation_id, home.role) == (CONGREGATION, SpecialRole.GEMEINDEVORSTEHER)
    assert leader.home_assignment is home


def test_a_district_level_leader_has_a_home_assignment_without_congregation() -> None:
    leader = Leader.create(name="Anna", district_id=DISTRICT)
    assert leader.home_assignment is not None
    assert leader.home_assignment.congregation_id is None and leader.home_assignment.role is None


def test_the_transitional_accessors_follow_the_home_assignment() -> None:
    leader = Leader.create(name="Hans", district_id=DISTRICT, congregation_id=CONGREGATION)
    other = LeaderAssignment.create(leader.id, DISTRICT, uuid.uuid4(), SpecialRole.GEMEINDEVORSTEHER)
    leader.assignments.append(other)
    assert leader.congregation_id == CONGREGATION and leader.special_role is None
    new_home = uuid.uuid4()
    leader.congregation_id = new_home
    leader.special_role = SpecialRole.BEZIRKSVORSTEHER
    assert leader.home_assignment.congregation_id == new_home
    assert leader.home_assignment.role == SpecialRole.BEZIRKSVORSTEHER
    assert other.role == SpecialRole.GEMEINDEVORSTEHER  # other assignments are untouched


def test_without_a_home_flag_the_first_assignment_stands_in_and_a_setter_creates_one() -> None:
    leader = Leader.create(name="Hans", district_id=DISTRICT)
    leader.assignments.clear()
    assert leader.home_assignment is None and leader.congregation_id is None
    leader.congregation_id = CONGREGATION
    assert [a.is_home for a in leader.assignments] == [True]
    assert leader.congregation_id == CONGREGATION
