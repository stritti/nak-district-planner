from datetime import UTC, datetime

import httpx
import pytest

from app.adapters.calendar.caldav_connector import CalDAVConnector
from app.adapters.calendar.google_connector import GoogleCalendarConnector
from app.adapters.calendar.ical_connector import ICalConnector
from app.adapters.calendar.microsoft_connector import MicrosoftGraphCalendarConnector
from app.domain.models.raw_calendar_event import RawCalendarEvent
from app.domain.ports.calendar import CalendarConnectorError


def event(resource_id="resource"):
    return RawCalendarEvent("uid", "title", datetime.now(UTC), datetime.now(UTC), None, "hash", False, '"etag"', resource_id)


@pytest.mark.parametrize("connector_type", [GoogleCalendarConnector, MicrosoftGraphCalendarConnector, CalDAVConnector])
@pytest.mark.parametrize("status", [204, 404, 410, 412, 500])
async def test_conditional_delete_and_error_propagation(connector_type, status):
    requests = []
    def handler(request):
        requests.append(request)
        return httpx.Response(status)
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        connector = connector_type(client)
        operation = connector.delete_event({"access_token": "test", "url": "https://calendar.test/cal/"}, event())
        if status >= 400 and status not in (404, 410):
            with pytest.raises(CalendarConnectorError):
                await operation
        else:
            await operation
    assert requests[0].method == "DELETE"
    assert requests[0].headers["If-Match"] == '"etag"'


@pytest.mark.parametrize("connector_type", [MicrosoftGraphCalendarConnector, CalDAVConnector])
async def test_missing_resource_refuses_delete(connector_type):
    async with httpx.AsyncClient(transport=httpx.MockTransport(lambda _: httpx.Response(204))) as client:
        with pytest.raises(CalendarConnectorError):
            await connector_type(client).delete_event({}, event(None))


async def test_caldav_does_not_forward_credentials_to_external_href():
    async with httpx.AsyncClient(transport=httpx.MockTransport(lambda _: pytest.fail("must not send"))) as client:
        with pytest.raises(CalendarConnectorError):
            await CalDAVConnector(client).delete_event({"url": "https://calendar.test/cal/"}, event("https://other.test/cal/item"))


async def test_ics_is_read_only():
    async with httpx.AsyncClient(transport=httpx.MockTransport(lambda _: httpx.Response(204))) as client:
        with pytest.raises(CalendarConnectorError):
            await ICalConnector(client).delete_event({}, event())
