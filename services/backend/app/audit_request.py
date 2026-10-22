# SPDX-FileCopyrightText: 2026 Stephan Strittmatter
# SPDX-License-Identifier: AGPL-3.0-only

"""Request-scoped state shared by the HTTP audit middleware and the session dependency.

The middleware starts a state before the route runs. The session dependency
reads it just before the commit; the domain audit hook marks it when it writes
an entry. That is how a successful write gets exactly one audit entry: the
domain entry if its aggregate has one, otherwise one inserted into the same
transaction. The state is a mutable object in a context variable, so the child
task that runs the route sees the changes the middleware reads afterwards.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from contextvars import ContextVar
from dataclasses import dataclass
from typing import Any

# Inserts the request's HTTP audit entry on the given session (set by the middleware).
TransactionEntry = Callable[[Any], Awaitable[None]]


@dataclass
class AuditRequestState:
    """What has been audited for the current request so far."""

    domain_audit_written: bool = False
    transaction_entry_written: bool = False
    transaction_entry: TransactionEntry | None = None

    @property
    def covered(self) -> bool:
        """The request already has an audit entry in its own transaction."""
        return self.domain_audit_written or self.transaction_entry_written


_current: ContextVar[AuditRequestState | None] = ContextVar("audit_request_state", default=None)


def begin_request_audit() -> AuditRequestState:
    state = AuditRequestState()
    _current.set(state)
    return state


def end_request_audit() -> None:
    _current.set(None)


def current_request_audit() -> AuditRequestState | None:
    return _current.get()


def mark_domain_audit() -> None:
    """Record that the current request's transaction carries a domain audit entry."""
    state = _current.get()
    if state is not None:
        state.domain_audit_written = True
