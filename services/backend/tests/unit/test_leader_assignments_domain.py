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


def test_congregation_ids_collects_every_assigned_congregation_but_not_the_district_level() -> None:
    leader = Leader.create(name="Hans", district_id=DISTRICT, congregation_id=CONGREGATION)
    other = uuid.uuid4()
    leader.assignments.append(LeaderAssignment.create(leader.id, DISTRICT, other))
    leader.assignments.append(LeaderAssignment.create(leader.id, DISTRICT, None))
    assert leader.congregation_ids == {CONGREGATION, other}


def test_without_a_home_flag_the_first_assignment_stands_in() -> None:
    leader = Leader.create(name="Hans", district_id=DISTRICT, congregation_id=CONGREGATION)
    leader.home_assignment.is_home = False
    assert leader.home_assignment is leader.assignments[0]
    leader.assignments.clear()
    assert leader.home_assignment is None and leader.congregation_ids == set()
