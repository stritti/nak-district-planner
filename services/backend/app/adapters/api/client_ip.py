# SPDX-FileCopyrightText: 2026 Stephan Strittmatter
# SPDX-License-Identifier: AGPL-3.0-only

"""Single source of truth for the client IP used by rate limiting and audit."""

from __future__ import annotations

import ipaddress
from functools import lru_cache

from starlette.requests import Request

from app.config import settings


@lru_cache(maxsize=8)
def _networks(value: str) -> tuple[ipaddress.IPv4Network | ipaddress.IPv6Network, ...]:
    return tuple(
        ipaddress.ip_network(net.strip(), strict=False) for net in value.split(",") if net.strip()
    )


def _parse_ip(value: str | None) -> ipaddress.IPv4Address | ipaddress.IPv6Address | None:
    try:
        return ipaddress.ip_address((value or "").strip())
    except ValueError:
        return None


def get_client_ip(request: Request) -> str | None:
    """Return the TCP peer, or nginx's X-Real-IP when the peer is a trusted proxy.

    X-Forwarded-For is never read: its leftmost entries are client-controlled.
    """
    peer = request.client.host if request.client else None
    peer_ip = _parse_ip(peer)
    if peer_ip is not None and any(peer_ip in net for net in _networks(settings.trusted_proxies)):
        real_ip = _parse_ip(request.headers.get("x-real-ip"))
        if real_ip is not None:
            return str(real_ip)
    return peer
