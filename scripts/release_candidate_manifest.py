#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Stephan Strittmatter
# SPDX-License-Identifier: AGPL-3.0-only

"""Store and reuse a verified backend/frontend digest pair on a draft release.

The release asset is uploaded once, before any version tags are promoted.
Retries reuse that exact pair and never overwrite the saved manifest.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import tempfile
from pathlib import Path

ASSET_NAME = "nak-release-candidates.json"
DIGEST_PATTERN = re.compile(r"sha256:[0-9a-f]{64}\Z")
REVISION_PATTERN = re.compile(r"[0-9a-f]{40}(?:[0-9a-f]{24})?\Z")
TAG_PATTERN = re.compile(r"v[0-9]+\.[0-9]+\.[0-9]+(?:-[0-9A-Za-z][0-9A-Za-z.-]*)?\Z")


def run(*args: str) -> str:
    """Execute GitHub CLI without shell expansion and fail on API errors."""
    return subprocess.run(args, check=True, capture_output=True, text=True).stdout.strip()


def digest_pair(backend: str, frontend: str) -> dict[str, str]:
    """Reject incomplete or invalid artifact pairs before persisting."""
    for value in (backend, frontend):
        if DIGEST_PATTERN.fullmatch(value) is None:
            raise ValueError(f"Invalid candidate digest: {value}")
    return {"backend": backend, "frontend": frontend}


def payload(tag: str, revision: str, registry: str, images: dict[str, str]) -> dict:
    """Create an immutable pairing with tag, checkout and registry identity."""
    if TAG_PATTERN.fullmatch(tag) is None:
        raise ValueError(f"Invalid candidate tag: {tag}")
    if REVISION_PATTERN.fullmatch(revision) is None:
        raise ValueError(f"Invalid commit revision: {revision}")
    if not re.fullmatch(r"ghcr\.io/[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", registry):
        raise ValueError(f"Invalid image registry: {registry}")
    if set(images) != {"backend", "frontend"}:
        raise ValueError("Candidate manifest must contain both services")
    return {
        "schema": 1, "tag": tag, "revision": revision, "registry": registry,
        "images": digest_pair(images["backend"], images["frontend"]),
    }


def validate(saved: dict, *, tag: str, revision: str, registry: str) -> dict[str, str]:
    """Refuse a different release tag, source commit or swapped service digest."""
    if not isinstance(saved, dict) or set(saved) != {
        "schema", "tag", "revision", "registry", "images",
    }:
        raise ValueError("Unexpected candidate manifest fields")
    if saved["schema"] != 1:
        raise ValueError("Unsupported candidate manifest schema")
    expected = payload(tag, revision, registry, saved["images"])
    if saved != expected:
        raise ValueError("Candidate manifest does not match the tagged checkout")
    return expected["images"]


def write_outputs(output: Path, *, reuse: bool, images: dict[str, str] | None) -> None:
    """Write only validated, single-line digest values to GitHub Actions."""
    values = [f"reuse={'true' if reuse else 'false'}"]
    if images is not None:
        values.extend(f"{name}_digest={digest}" for name, digest in images.items())
    with output.open("a", encoding="utf-8") as stream:
        stream.write("\n".join(values) + "\n")


def check(tag: str, revision: str, registry: str, output: Path) -> bool:
    """Reuse the draft asset if available, or request a fresh paired build."""
    result = json.loads(run("gh", "release", "view", tag, "--json", "assets"))
    assets = result.get("assets", [])
    if not isinstance(assets, list):
        raise ValueError("GitHub returned invalid release assets")
    existing = [item for item in assets if isinstance(item, dict) and item.get("name") == ASSET_NAME]
    if len(existing) > 1:
        raise ValueError("Duplicate release candidate manifests")
    if not existing:
        write_outputs(output, reuse=False, images=None)
        return False
    with tempfile.TemporaryDirectory(prefix="nak-release-candidates-") as directory:
        run("gh", "release", "download", tag, "--pattern", ASSET_NAME, "--dir", directory)
        saved = json.loads((Path(directory) / ASSET_NAME).read_text(encoding="utf-8"))
    images = validate(saved, tag=tag, revision=revision, registry=registry)
    write_outputs(output, reuse=True, images=images)
    return True


def save(tag: str, revision: str, registry: str, output: Path, backend: str, frontend: str) -> None:
    """Upload the digest pair without clobbering an existing release asset."""
    images = digest_pair(backend, frontend)
    manifest = payload(tag, revision, registry, images)
    with tempfile.TemporaryDirectory(prefix="nak-release-candidates-") as directory:
        path = Path(directory) / ASSET_NAME
        path.write_text(json.dumps(manifest, sort_keys=True) + "\n", encoding="utf-8")
        run("gh", "release", "upload", tag, str(path))
    write_outputs(output, reuse=False, images=images)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("check", "save"))
    parser.add_argument("--tag", required=True)
    parser.add_argument("--revision", required=True)
    parser.add_argument("--registry", required=True)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--backend-digest")
    parser.add_argument("--frontend-digest")
    args = parser.parse_args()
    if args.action == "check":
        check(args.tag, args.revision, args.registry, args.output)
    else:
        if args.backend_digest is None or args.frontend_digest is None:
            parser.error("save requires both backend and frontend digests")
        save(
            args.tag, args.revision, args.registry, args.output,
            args.backend_digest, args.frontend_digest,
        )


if __name__ == "__main__":
    main()
