"""Shared conditional HTTP deletion without suppressing provider errors."""

import httpx

from app.domain.ports.calendar import CalendarConnectorError


async def delete_resource(client: httpx.AsyncClient, url: str, **kwargs) -> None:
    response = await client.delete(url, **kwargs)
    if response.status_code in (404, 410):
        return  # Retrying an already completed deletion is safe.
    try:
        response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        raise CalendarConnectorError(f"Kalender-Löschung fehlgeschlagen: HTTP {response.status_code}") from exc
