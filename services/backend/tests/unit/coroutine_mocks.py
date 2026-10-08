"""Mocks for ``asyncio.run`` that never leak un-awaited coroutines.

Celery tasks call ``asyncio.run(_run_as_system_worker(_run()))``.  Patching
``asyncio.run`` with a plain ``MagicMock`` leaves both coroutine objects
un-awaited, which surfaces as ``RuntimeWarning: coroutine ... was never
awaited`` whenever the garbage collector happens to run.
"""

from __future__ import annotations

import inspect
from unittest.mock import MagicMock


def close_coroutine(coro: object) -> None:
    """Close *coro* and any not-yet-started coroutines passed to it as arguments."""
    if not inspect.iscoroutine(coro):
        return
    frame = coro.cr_frame
    if frame is not None and inspect.getcoroutinestate(coro) == inspect.CORO_CREATED:
        for value in list(frame.f_locals.values()):
            close_coroutine(value)
    coro.close()


class CoroutineClosingMock(MagicMock):
    """``MagicMock`` that closes coroutine arguments before applying the configured behaviour.

    Use as ``patch("app.application.tasks.asyncio.run", new_callable=CoroutineClosingMock)``;
    ``return_value`` and ``side_effect`` keep working as usual.
    """

    def __call__(self, /, *args, **kwargs):
        for arg in (*args, *kwargs.values()):
            close_coroutine(arg)
        return super().__call__(*args, **kwargs)
