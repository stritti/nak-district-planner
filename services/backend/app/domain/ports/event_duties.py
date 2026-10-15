# SPDX-FileCopyrightText: 2026 Stephan Strittmatter
# SPDX-License-Identifier: AGPL-3.0-only

"""Persistence port; callers own the encompassing transaction."""

from abc import ABC, abstractmethod


class EventDutiesRepository(ABC):
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
