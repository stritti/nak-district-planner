from __future__ import annotations

from collections.abc import Callable, Iterable

from app.domain.planning.conflict_result import ConflictContext, ConflictResult
from app.domain.planning.conflict_rules import (
    leader_available,
    no_double_booking,
    role_requirement_check,
    travel_time_check,
)

ConflictRule = Callable[[ConflictContext], ConflictResult | None]


class ConflictService:
    """Run planning conflict rules against a domain context."""

    def __init__(self, rules: Iterable[ConflictRule] | None = None) -> None:
        self._rules = tuple(
            rules
            if rules is not None
            else (
                no_double_booking,
                travel_time_check,
                role_requirement_check,
                leader_available,
            )
        )

    def check(self, context: ConflictContext) -> list[ConflictResult]:
        return [result for rule in self._rules if (result := rule(context)) is not None]
