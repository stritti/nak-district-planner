# SPDX-FileCopyrightText: 2026 Stephan Strittmatter
# SPDX-License-Identifier: AGPL-3.0-only

"""Persistence port; callers own the encompassing transaction."""

from abc import ABC, abstractmethod


class EventDutiesRepository(ABC):
    """Duty persistence contract.

    Write use-cases may pass an expected congregation to guard the slot scope
    across authorization and row locking; ``None`` is a real district scope,
    while an omitted expectation deliberately disables that TOCTOU check.
    """

    @abstractmethod
    async def catalog(self, district_id, congregation_id=None):
        raise NotImplementedError

    @abstractmethod
    async def list_assignments(self, slot_ids):
        raise NotImplementedError

    @abstractmethod
    async def count_assignments(self, slot_id, category_id):
        raise NotImplementedError

    @abstractmethod
    async def get_slot(self, slot_id, district_id):
        raise NotImplementedError

    @abstractmethod
    async def lock_slot(self, slot_id, district_id):
        raise NotImplementedError

    @abstractmethod
    async def lock_category(self, category_id, district_id):
        raise NotImplementedError

    @abstractmethod
    async def save_category(self, category):
        raise NotImplementedError

    @abstractmethod
    async def save_configuration(self, configuration):
        raise NotImplementedError

    @abstractmethod
    async def delete_configuration(self, district_id, congregation_id, category_id):
        raise NotImplementedError

    @abstractmethod
    async def get_assignment(self, assignment_id):
        raise NotImplementedError

    @abstractmethod
    async def lock_assignment(self, assignment_id):
        raise NotImplementedError

    @abstractmethod
    async def save_assignment(self, assignment):
        raise NotImplementedError

    @abstractmethod
    async def delete_assignment(self, assignment_id):
        raise NotImplementedError

    @abstractmethod
    async def eligible_users(self, district_id, congregation_id):
        raise NotImplementedError

    @abstractmethod
    async def eligible_user_display_name(self, district_id, congregation_id, user_sub):
        raise NotImplementedError

    @abstractmethod
    async def list_suggestions(self, district_id, congregation_id, category_id):
        raise NotImplementedError

    @abstractmethod
    async def remember(self, district_id, congregation_id, category_id, name, activate=False):
        raise NotImplementedError

    @abstractmethod
    async def get_suggestion(self, suggestion_id):
        raise NotImplementedError

    @abstractmethod
    async def save_suggestion(self, suggestion):
        raise NotImplementedError

    @abstractmethod
    async def slot_schedule(self, slot_id):
        """Planned date/time and actual instance times of a slot as a ``ScheduledService``."""

    @abstractmethod
    async def list_identity_schedule(
        self, district_id, *, linked_user_sub, normalized_name, leader_id, window_start,
        window_end, exclude_slot_id,
    ):
        """Other duties of one person near a time window, as ``ScheduledDuty`` values.

        ``linked_user_sub`` and ``leader_id`` match strongly (``leader_id`` also finds the
        leader's service assignments), ``normalized_name`` only by typed name.
        Duties of ``exclude_slot_id`` are ignored (several duties on one event are fine).
        """

    @abstractmethod
    async def get_leader(self, district_id, leader_id):
        """The leader of this district, or ``None``."""

    @abstractmethod
    async def list_leaders(self, district_id):
        """Leaders of this district, ordered by name."""

    @abstractmethod
    async def lock_leader(self, leader_id):
        """Serialize bookings of one leader until the transaction ends.

        Service assignments take the same lock, so a duty and a service of the
        same leader cannot both pass their conflict checks concurrently.
        """

    @abstractmethod
    async def lock_account(self, user_sub):
        """Serialize bookings of one account (a leader's linked account included)."""

