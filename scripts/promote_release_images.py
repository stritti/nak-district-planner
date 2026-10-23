#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Stephan Strittmatter
# SPDX-License-Identifier: AGPL-3.0-only

"""Promote two verified GHCR images, then publish their draft GitHub release.

Builds push only run-scoped staging tags. Version tags are write-once; mutable
aliases are promoted after *both* version tags exist. Failed alias promotion or
release publication restores previous aliases where possible. GitHub and GHCR
cannot update two packages atomically: production must deploy exact versions.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from dataclasses import dataclass

DIGEST_PATTERN = re.compile(r"^sha256:[0-9a-f]{64}$")
VERSION_PATTERN = re.compile(
    r"^v(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)"
    r"(?:-([0-9A-Za-z][0-9A-Za-z.-]*))?$"
)
INSPECT_DIGEST = re.compile(r"^Digest:\s*(sha256:[0-9a-f]{64})\s*$", re.MULTILINE)
NOT_FOUND = ("manifest unknown", "manifest not found", "404 not found", "name unknown")


class PromotionError(RuntimeError):
    """An unsafe or incomplete promotion; leave the GitHub release as draft."""


def command(*args: str, allow_missing: bool = False) -> str | None:
    """Run trusted CLI arguments without shell interpretation."""
    result = subprocess.run(args, capture_output=True, text=True, check=False)
    if result.returncode == 0:
        return result.stdout.strip()
    message = result.stderr.strip()
    if allow_missing and any(marker in message.lower() for marker in NOT_FOUND):
        return None
    raise PromotionError(f"{' '.join(args[:3])} failed: {message or result.returncode}")


@dataclass(frozen=True)
class Image:
    service: str
    digest: str


class ReleasePromoter:
    def __init__(self, registry: str, tag: str, backend_digest: str, frontend_digest: str):
        match = VERSION_PATTERN.fullmatch(tag)
        if match is None:
            raise PromotionError(f"Invalid release tag: {tag}")
        for digest in (backend_digest, frontend_digest):
            if DIGEST_PATTERN.fullmatch(digest) is None:
                raise PromotionError(f"Invalid image digest: {digest}")
        self.registry = registry.rstrip("/")
        self.tag = tag
        self.version = tag.removeprefix("v")
        self.stable = match.group(4) is None
        self.images = (Image("backend", backend_digest), Image("frontend", frontend_digest))

    def repository(self, image: Image) -> str:
        return f"{self.registry}/{image.service}"

    def digest_of(self, reference: str) -> str | None:
        output = command("docker", "buildx", "imagetools", "inspect", reference, allow_missing=True)
        if output is None:
            return None
        match = INSPECT_DIGEST.search(output)
        if match is None:
            raise PromotionError(f"No manifest digest in inspect output for {reference}")
        return match.group(1)

    def tag_image(self, repository: str, name: str, digest: str) -> None:
        """Copy a manifest by digest and verify the resulting target digest."""
        command(
            "docker", "buildx", "imagetools", "create", "--prefer-index=false",
            "--tag", f"{repository}:{name}", f"{repository}@{digest}",
        )
        actual = self.digest_of(f"{repository}:{name}")
        if actual != digest:
            raise PromotionError(
                f"Digest mismatch for {repository}:{name}: expected {digest}, got {actual}"
            )

    def aliases(self) -> tuple[str, ...]:
        if not self.stable:
            return ()
        major, minor, *_ = self.version.split(".")
        return (f"{major}.{minor}", major, "latest")

    def verify_staging(self) -> None:
        """Fail before writing any version or alias if a build is missing."""
        for image in self.images:
            repo = self.repository(image)
            if self.digest_of(f"{repo}@{image.digest}") != image.digest:
                raise PromotionError(f"Missing staged {image.service} digest {image.digest}")

    def ensure_version_tags(self) -> None:
        """Never rewrite a published version, including on workflow retries."""
        for image in self.images:
            repo = self.repository(image)
            old = self.digest_of(f"{repo}:{self.version}")
            if old is not None and old != image.digest:
                raise PromotionError(
                    f"{repo}:{self.version} already points to {old}; "
                    "version tags are immutable. Recover with the original digest."
                )
        for image in self.images:
            repo = self.repository(image)
            if self.digest_of(f"{repo}:{self.version}") is None:
                self.tag_image(repo, self.version, image.digest)

    def ensure_draft(self) -> None:
        status = command("gh", "release", "view", self.tag, "--json", "isDraft", "--jq", ".isDraft")
        if status != "true":
            raise PromotionError(f"{self.tag} is not a draft release; refusing promotion")

    def run(self) -> None:
        self.ensure_draft()
        self.verify_staging()
        self.ensure_version_tags()

        # Capture all previous aliases before changing any of them.
        aliases = self.aliases()
        previous = {
            (image.service, alias): self.digest_of(f"{self.repository(image)}:{alias}")
            for image in self.images for alias in aliases
        }
        changed: list[tuple[Image, str]] = []
        try:
            for image in self.images:
                repo = self.repository(image)
                for alias in aliases:
                    if previous[(image.service, alias)] != image.digest:
                        # Track *before* the operation; it might have written
                        # a tag before failing its post-write verification.
                        changed.append((image, alias))
                        self.tag_image(repo, alias, image.digest)
            # Draft -> public is the last, fail-closed release-readiness gate.
            self.ensure_draft()
            command("gh", "release", "edit", self.tag, "--draft=false")
        except (PromotionError, OSError):
            failures = []
            for image, alias in reversed(changed):
                old = previous[(image.service, alias)]
                if old is None:
                    failures.append(f"{self.repository(image)}:{alias} had no previous tag")
                    continue
                try:
                    self.tag_image(self.repository(image), alias, old)
                except (PromotionError, OSError) as exc:
                    failures.append(f"{image.service}:{alias}: {exc}")
            if failures:
                print(
                    "Manual alias recovery required: " + "; ".join(failures),
                    file=sys.stderr,
                )
            raise


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--registry", required=True, help="ghcr.io/OWNER/REPO")
    parser.add_argument("--tag", required=True, help="vMAJOR.MINOR.PATCH[-PRERELEASE]")
    parser.add_argument("--backend-digest", required=True)
    parser.add_argument("--frontend-digest", required=True)
    args = parser.parse_args()
    ReleasePromoter(args.registry, args.tag, args.backend_digest, args.frontend_digest).run()


if __name__ == "__main__":
    main()
