"""Shared HTTP resilience helpers for calendar provider adapters."""

from __future__ import annotations

from collections.abc import Awaitable, Callable

import httpx
from tenacity import (
    AsyncRetrying,
    retry_if_exception,
    stop_after_attempt,
    wait_exponential_jitter,
)

from app.domain.ports.calendar import CalendarConnectorError

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
    except httpx.HTTPStatusError as exc:
        raise CalendarConnectorError(
            f"HTTP {exc.response.status_code} beim Laden des {provider} Kalenders"
        ) from exc
    except httpx.RequestError as exc:
        raise CalendarConnectorError(
            f"Transportfehler beim Laden des {provider} Kalenders"
        ) from exc
    raise CalendarConnectorError(
        f"Unbekannter Fehler beim Laden des {provider} Kalenders"
    )
