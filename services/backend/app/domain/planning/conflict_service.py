from __future__ import annotations

from collections.abc import Callable, Iterable

from app.domain.planning.conflict_result import ConflictContext, ConflictResult

ConflictRule = Callable[[ConflictContext], ConflictResult | None]


class ConflictService:
    """Run planning conflict rules against a domain context."""

    def __init__(self, rules: Iterable[ConflictRule]) -> None:
        self._rules = tuple(rules)

    def check(self, context: ConflictContext) -> list[ConflictResult]:
        return [result for rule in self._rules if (result := rule(context)) is not None]
