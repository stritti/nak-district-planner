#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Stephan Strittmatter
# SPDX-License-Identifier: AGPL-3.0-only

"""Safely inspect exported external-proxy/APM logs for an ICS canary token.

The token is read from stdin, never from command-line arguments or environment.
Only status messages are printed; paths, file contents and token stay private.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

_CHUNK_SIZE = 64 * 1024


def _contains_token(path: Path, token: bytes) -> bool:
    """Scan large binary logs without missing matches across chunk boundaries."""
    overlap = b""
    with path.open("rb") as source:
        while chunk := source.read(_CHUNK_SIZE):
            data = overlap + chunk
            if token in data:
                return True
            overlap = data[-(len(token) - 1) :] if len(token) > 1 else b""
    return False


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Check exported log files without displaying an ICS bearer token."
    )
    parser.add_argument(
        "--source", action="append", default=[], metavar="EXPORTED_LOG",
        help="A local log/APM export (repeat for every log and telemetry sink)",
    )
    args = parser.parse_args()
    if not args.source:
        print("INCOMPLETE: no log sources supplied", file=sys.stderr)
        return 2

    token = sys.stdin.buffer.readline(4097).rstrip(b"\r\n")
    if not 16 <= len(token) <= 4096:
        print("INCOMPLETE: invalid or absent canary input", file=sys.stderr)
        return 2

    leaks = 0
    for source in args.source:
        try:
            leaks += _contains_token(Path(source), token)
        except OSError:
            print("INCOMPLETE: one or more log sources cannot be read", file=sys.stderr)
            return 2

    if leaks:
        print("TOKEN FOUND: stop release; inspect retention and rotate exposed subscriptions")
        return 1
    print(f"PASS: token absent from {len(args.source)} sources")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
