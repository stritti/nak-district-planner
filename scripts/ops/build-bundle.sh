#!/usr/bin/env bash
# SPDX-FileCopyrightText: 2026 Stephan Strittmatter
# SPDX-License-Identifier: AGPL-3.0-only

# Build the deploy bundle that scripts/ops/install.sh installs on a production host.
#
#   scripts/ops/build-bundle.sh <version> <out-dir>
#
# Writes <out-dir>/nak-district-planner-deploy-<version>.tar.gz, <out-dir>/install.sh and
# <out-dir>/SHA256SUMS (checksums of both).
# The archive is reproducible: same sources and SOURCE_DATE_EPOCH give the same bytes, so a
# re-run of the release workflow uploads an identical asset. Needs GNU tar and gzip.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

# Everything a production host needs, and nothing else (no source code, no secrets).
BUNDLE_FILES=(
  LICENSE
  LICENSES/AGPL-3.0-only.txt
  LICENSES/MIT.txt
  docker-compose.prod.yml
  .env.example
  .env.db.example
  .env.keycloak.example
  .env.keycloak-db.example
  .env.docker
  .env.docker.frontend
  .env.docker.migrate
  deploy/compose/existing-keycloak.yml
  deploy/compose/existing-traefik.yml
  deploy/traefik/dynamic/app.yml
  deploy/traefik/dynamic/keycloak.yml
  scripts/backup.sh
  scripts/restore.sh
  scripts/ops/nakctl
  scripts/ops/lib.sh
  scripts/ops/nakops.py
  scripts/ops/install.sh
  scripts/ops/examples/backup-post-hook-rsync.sh
)

usage() {
  sed -n '6,12p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'
}

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
  usage
  exit 0
fi
(($# == 2)) || { usage >&2; exit 2; }

version="${1#v}"
out_dir="$2"
[[ "$version" =~ ^[0-9]+\.[0-9]+\.[0-9]+(-[0-9A-Za-z.]+)?$ ]] || {
  echo "FEHLER: ungültige Version: $1" >&2
  exit 2
}

epoch="${SOURCE_DATE_EPOCH:-$(git -C "$REPO_ROOT" log -1 --format=%ct 2>/dev/null || echo 0)}"
name="nak-district-planner-deploy-$version"
prefix="nak-district-planner-$version"

stage="$(mktemp -d)"
trap 'rm -rf "$stage"' EXIT
mkdir -p "$stage/$prefix" "$out_dir"

for file in "${BUNDLE_FILES[@]}"; do
  [[ -f "$REPO_ROOT/$file" ]] || { echo "FEHLER: $file fehlt" >&2; exit 3; }
  mkdir -p "$stage/$prefix/$(dirname "$file")"
  cp "$REPO_ROOT/$file" "$stage/$prefix/$file"
  if [[ -x "$REPO_ROOT/$file" ]]; then
    chmod 0755 "$stage/$prefix/$file"
  else
    chmod 0644 "$stage/$prefix/$file"
  fi
done
printf '%s\n' "$version" >"$stage/$prefix/VERSION"
printf '%s\n' "${BUNDLE_FILES[@]}" VERSION MANIFEST | LC_ALL=C sort >"$stage/$prefix/MANIFEST"
chmod 0644 "$stage/$prefix/VERSION" "$stage/$prefix/MANIFEST"
find "$stage/$prefix" -type d -exec chmod 0755 {} +

tar --sort=name --mtime="@$epoch" --owner=0 --group=0 --numeric-owner --format=gnu \
  -C "$stage" -cf - "$prefix" | gzip -n -9 >"$out_dir/$name.tar.gz"
cp "$REPO_ROOT/scripts/ops/install.sh" "$out_dir/install.sh"
chmod 0755 "$out_dir/install.sh"
(cd "$out_dir" && sha256sum "$name.tar.gz" install.sh >SHA256SUMS)
echo "$out_dir/$name.tar.gz"
