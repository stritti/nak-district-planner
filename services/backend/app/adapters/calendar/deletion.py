"""Shared conditional HTTP deletion without suppressing provider errors."""

import httpx

from app.domain.ports.calendar import CalendarConnectorError


async def delete_resource(client: httpx.AsyncClient, url: str, **kwargs) -> None:
    try:
        response = await client.delete(url, **kwargs)
    except httpx.RequestError as exc:
        raise CalendarConnectorError("Transportfehler bei Kalender-Löschung") from exc
    if response.status_code in (404, 410):
        return
    try:
        response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        raise CalendarConnectorError(
            f"Kalender-Löschung fehlgeschlagen: HTTP {response.status_code}"
        ) from exc
