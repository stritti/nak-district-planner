"""Adapter for checking Docker image versions on GitHub Container Registry."""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from typing import Sequence

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

SEMVER_PATTERN = re.compile(r"^v?(\d+)\.(\d+)\.(\d+)$")


@dataclass(frozen=True, order=True)
class SemVer:
    """Simple SemVer value object for comparison."""

    major: int
    minor: int
    patch: int

    @classmethod
    def parse(cls, tag: str) -> SemVer | None:
        """Parse a SemVer tag like '0.4.5' or 'v0.4.5'."""
        match = SEMVER_PATTERN.match(tag)
        if not match:
            return None
        return cls(
            major=int(match.group(1)),
            minor=int(match.group(2)),
            patch=int(match.group(3)),
        )

    def __str__(self) -> str:
        return f"{self.major}.{self.minor}.{self.patch}"


def parse_semver_tags(tags: Sequence[str]) -> list[SemVer]:
    """Filter and parse a list of tag strings, returning only valid SemVers."""
    result: list[SemVer] = []
    for tag in tags:
        parsed = SemVer.parse(tag)
        if parsed is not None:
            result.append(parsed)
    return result


def latest_semver(tags: Sequence[str]) -> str | None:
    """Return the highest SemVer tag from a list of tag strings.

    Returns the tag *without* the 'v' prefix (e.g. '0.5.0').
    Returns None if no valid SemVer tags are found.
    """
    parsed = parse_semver_tags(tags)
    if not parsed:
        return None
    parsed.sort(reverse=True)
    return str(parsed[0])


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

    def fetch_latest_version(self, service: str = "backend") -> str | None:
        """Fetch and return the latest SemVer version for a service image."""
        tags = self.fetch_tags(service)
        return latest_semver(tags)
