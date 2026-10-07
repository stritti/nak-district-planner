"""Shared HTTP resilience helpers for calendar provider adapters."""

from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable

import httpx
from tenacity import (
    AsyncRetrying,
    retry_if_exception,
    stop_after_attempt,
    wait_exponential_jitter,
)

from app.domain.ports.calendar import CalendarConnectorError

logger = logging.getLogger(__name__)

_RETRYABLE_STATUS = {408, 425, 429, 500, 502, 503, 504}


def _is_retryable(exc: BaseException) -> bool:
    if isinstance(exc, httpx.RequestError):
        return True
    return isinstance(exc, httpx.HTTPStatusError) and exc.response.status_code in _RETRYABLE_STATUS


async def resilient_request(
    request: Callable[[], Awaitable[httpx.Response]],
    *,
    provider: str,
) -> httpx.Response:
    """Execute one provider request with bounded retries for transient failures."""
    try:
        async for attempt in AsyncRetrying(
            retry=retry_if_exception(_is_retryable),
            stop=stop_after_attempt(3),
            wait=wait_exponential_jitter(initial=0.25, max=2.0),
            reraise=True,
        ):
            with attempt:
                response = await request()
                response.raise_for_status()
                return response
    except httpx.HTTPError as exc:
        # One generic message for status and transport failures: distinct texts
        # would act as a port/service oracle (#463). Details stay in the log,
        # without URL or credentials.
        status = exc.response.status_code if isinstance(exc, httpx.HTTPStatusError) else None
        logger.warning(
            "%s calendar request failed (%s, HTTP status %s)", provider, type(exc).__name__, status
        )
        raise CalendarConnectorError(f"{provider} Kalender konnte nicht geladen werden") from exc
    raise CalendarConnectorError(
        f"Unbekannter Fehler beim Laden des {provider} Kalenders"
    )
