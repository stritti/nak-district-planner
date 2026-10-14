# SPDX-FileCopyrightText: 2026 Stephan Strittmatter
# SPDX-License-Identifier: AGPL-3.0-only

"""Adapter for checking Docker image versions on GitHub Container Registry."""

from __future__ import annotations

import logging
import re
from collections.abc import Sequence
from dataclasses import dataclass

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

# SemVer 2.0 core + optional prerelease (``1.0.0-rc.1``), or a PEP 440
# pre-release suffix (``1.0.0rc1``) as reported by Python package metadata.
# SemVer build metadata / PEP 440 local versions (``+...``) are ignored for precedence.
SEMVER_PATTERN = re.compile(
    r"^v?(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)"
    r"(?:-((?:0|[1-9]\d*|\d*[A-Za-z-][0-9A-Za-z-]*)"
    r"(?:\.(?:0|[1-9]\d*|\d*[A-Za-z-][0-9A-Za-z-]*))*)"
    r"|(a|b|rc)(\d+))?(?:\+[0-9A-Za-z.-]+)?$"
)
_PEP440_PRE = {"a": "alpha", "b": "beta", "rc": "rc"}


@dataclass(frozen=True)
class SemVer:
    """SemVer value object with SemVer 2.0 precedence (prereleases included)."""

    major: int
    minor: int
    patch: int
    pre: tuple[str, ...] = ()

    @classmethod
    def parse(cls, tag: str) -> SemVer | None:
        """Parse ``0.4.5``, ``v1.0.0-rc.1`` or PEP 440 ``1.0.0rc1`` (→ ``1.0.0-rc.1``)."""
        match = SEMVER_PATTERN.match(tag)
        if not match:
            return None
        major, minor, patch, pre, pep_kind, pep_num = match.groups()
        if pep_kind:
            pre = f"{_PEP440_PRE[pep_kind]}.{int(pep_num)}"
        return cls(int(major), int(minor), int(patch), tuple(pre.split(".")) if pre else ())

    @property
    def is_prerelease(self) -> bool:
        """True for versions with a prerelease part."""
        return bool(self.pre)

    def _key(self) -> tuple:
        # Final release ranks above any prerelease of the same core version;
        # numeric identifiers compare numerically and rank below alphanumerics.
        pre = tuple((0, int(p), "") if p.isdigit() else (1, 0, p) for p in self.pre)
        return (self.major, self.minor, self.patch, not self.pre, pre)

    def __lt__(self, other: SemVer) -> bool:
        """Compare by SemVer precedence."""
        return self._key() < other._key()

    def __str__(self) -> str:
        """Return the canonical SemVer string, e.g. ``1.0.0-rc.1``."""
        core = f"{self.major}.{self.minor}.{self.patch}"
        return f"{core}-{'.'.join(self.pre)}" if self.pre else core


def parse_semver_tags(tags: Sequence[str]) -> list[SemVer]:
    """Filter and parse a list of tag strings, returning only valid SemVers."""
    return [v for v in map(SemVer.parse, tags) if v is not None]


def latest_semver(tags: Sequence[str], current: str | None = None) -> str | None:
    """Return the highest SemVer tag (without ``v`` prefix) or None.

    Policy: prerelease tags are only considered when ``current`` is itself a
    prerelease; installations on a stable release are only offered stable
    releases. Non-SemVer tags (``latest``, ``sha-…``) are ignored.
    """
    cur = SemVer.parse(current) if current else None
    allow_pre = cur is not None and cur.is_prerelease
    candidates = [v for v in parse_semver_tags(tags) if allow_pre or not v.is_prerelease]
    return str(max(candidates)) if candidates else None


def is_newer(latest: str | None, current: str) -> bool:
    """True only if ``latest`` is strictly newer than ``current`` (never a downgrade).

    Fails safe: an unparseable ``current`` never gets an update offer.
    """
    new = SemVer.parse(latest) if latest else None
    if new is None:
        return False
    cur = SemVer.parse(current)
    return cur is not None and cur < new


class GhcrTagFetcher:
    """Fetches Docker image tags from GitHub Container Registry."""

    BASE_URL = "https://ghcr.io/v2"

    def __init__(self, owner: str | None = None, repo: str | None = None) -> None:
        self.owner = owner or settings.ghcr_owner
        self.repo = repo or settings.ghcr_repo

    def _image(self, service: str) -> str:
        return f"{self.owner}/{self.repo}/{service}"

    def fetch_tags(self, service: str = "backend") -> list[str]:
        """Fetch all tags for a given service image from ghcr.io.

        Returns a list of tag strings (e.g. ['0.4.5', '0.5.0', 'latest']).
        Returns an empty list on failure.
        """
        url = f"{self.BASE_URL}/{self._image(service)}/tags/list"
        try:
            with httpx.Client(timeout=10.0) as client:
                resp = client.get(url)
                resp.raise_for_status()
                data = resp.json()
                tags: list[str] = data.get("tags", [])
                return tags
        except httpx.HTTPError as e:
            logger.warning("Failed to fetch tags from ghcr.io: %s", e)
            return []
        except Exception as e:
            logger.exception("Unexpected error fetching ghcr.io tags: %s", e)
            return []

    def fetch_latest_version(
        self, service: str = "backend", current: str | None = None
    ) -> str | None:
        """Fetch and return the latest SemVer version for a service image."""
        return latest_semver(self.fetch_tags(service), current)
