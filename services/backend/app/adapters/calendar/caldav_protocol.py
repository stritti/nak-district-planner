# SPDX-FileCopyrightText: 2026 Stephan Strittmatter
# SPDX-License-Identifier: AGPL-3.0-only

"""CalDAV protocol details: REPORT construction, multistatus parsing, hrefs, auth.

Everything DAV-specific lives here so that ``CalDAVConnector`` only orchestrates
requests and iCalendar normalization. Nothing in this module leaves the adapter.
"""

from __future__ import annotations

import posixpath
import xml.etree.ElementTree as XMLBuilder  # nosec B405 - builds XML only; parsing uses defusedxml
from dataclasses import dataclass
from datetime import UTC, datetime
from urllib.parse import unquote, urljoin, urlsplit

import defusedxml.ElementTree as SafeXML
from defusedxml import DefusedXmlException

from app.domain.ports.calendar import CalendarConnectorError

DAV = "DAV:"
CALDAV = "urn:ietf:params:xml:ns:caldav"
_NS = {"D": DAV, "C": CALDAV}


@dataclass(frozen=True)
class DavResource:
    """One calendar object from a multistatus response."""

    href: str | None
    etag: str | None
    calendar_data: str


@dataclass(frozen=True)
class DavAuth:
    """Request headers and httpx basic-auth tuple for one CalDAV account."""

    headers: dict[str, str]
    basic: tuple[str, str] | None

    def request_kwargs(self) -> dict:
        return {"headers": dict(self.headers), "auth": self.basic}


def dav_auth(credentials: dict) -> DavAuth:
    """Bearer token or username/password; anything else is refused."""
    if "access_token" in credentials:
        return DavAuth({"Authorization": f"Bearer {credentials['access_token']}"}, None)
    if "username" in credentials and "password" in credentials:
        return DavAuth({}, (str(credentials["username"]), str(credentials["password"])))
    raise CalendarConnectorError(
        "CalDAV credentials must include either access_token or username/password"
    )


def collection_url(credentials: dict) -> str:
    """The configured calendar collection, always with a trailing slash."""
    url_value = credentials.get("url")
    if not url_value:
        raise CalendarConnectorError("CalDAV Basis-URL fehlt in den Credentials")
    return str(url_value).rstrip("/") + "/"


def format_utc(value: datetime) -> str:
    """RFC 4791 date-time in UTC, e.g. ``20260301T100000Z``; naive values count as UTC."""
    value = value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)
    return value.strftime("%Y%m%dT%H%M%SZ")


def build_calendar_query(from_dt: datetime | None, to_dt: datetime | None) -> bytes:
    """calendar-query REPORT for VEVENTs overlapping the window.

    Built with an XML builder, never by string interpolation. RFC 4791 9.9:
    unset bounds are omitted, never sent as empty attributes.
    """
    XMLBuilder.register_namespace("D", DAV)
    XMLBuilder.register_namespace("C", CALDAV)
    query = XMLBuilder.Element(f"{{{CALDAV}}}calendar-query")
    prop = XMLBuilder.SubElement(query, f"{{{DAV}}}prop")
    XMLBuilder.SubElement(prop, f"{{{DAV}}}getetag")
    XMLBuilder.SubElement(prop, f"{{{CALDAV}}}calendar-data")
    calendars = XMLBuilder.SubElement(
        XMLBuilder.SubElement(query, f"{{{CALDAV}}}filter"),
        f"{{{CALDAV}}}comp-filter",
        name="VCALENDAR",
    )
    events = XMLBuilder.SubElement(calendars, f"{{{CALDAV}}}comp-filter", name="VEVENT")
    bounds = {
        name: format_utc(value)
        for name, value in (("start", from_dt), ("end", to_dt))
        if value is not None
    }
    if bounds:
        XMLBuilder.SubElement(events, f"{{{CALDAV}}}time-range", bounds)
    return XMLBuilder.tostring(query, encoding="utf-8", xml_declaration=True)


def parse_multistatus(content: bytes) -> list[DavResource]:
    """All ``D:response`` entries; hostile or malformed XML fails without details.

    defusedxml refuses DTDs with entities and external references, so neither
    entity expansion nor XXE can happen while parsing provider content.
    """
    try:
        root = SafeXML.fromstring(content)
    except (SafeXML.ParseError, DefusedXmlException) as exc:
        raise CalendarConnectorError("Ungültige XML-Antwort vom CalDAV Server") from exc
    return [
        DavResource(
            # Kept verbatim: both become stored identity/revision markers.
            href=response.findtext("D:href", namespaces=_NS),
            etag=response.findtext(".//D:getetag", namespaces=_NS),
            calendar_data=response.findtext(".//C:calendar-data", namespaces=_NS) or "",
        )
        for response in root.findall(".//D:response", _NS)
    ]


def resource_url(collection: str, href: str) -> str:
    """Absolute URL of a resource href, provided it stays inside the collection.

    Hrefs come from the server and are untrusted: another origin, dot segments
    (also percent-encoded), backslashes, a query, a fragment or the collection
    itself are refused.
    """
    target = urlsplit(urljoin(collection, href))
    source = urlsplit(collection)
    path = unquote(target.path)
    if (
        (target.scheme, target.netloc) != (source.scheme, source.netloc)
        or target.query
        or target.fragment
        or "\\" in path
        or posixpath.normpath(path) != path.rstrip("/")
        or not path.startswith(unquote(source.path))
        or path.rstrip("/") == unquote(source.path).rstrip("/")
    ):
        raise CalendarConnectorError("CalDAV resource liegt außerhalb des Kalenders")
    return target.geturl()
