#!/usr/bin/env bash
# Create an encrypted PostgreSQL backup of the NAK District Planner database.
#
# Runs pg_dump inside the running `db` container (avoids requiring PostgreSQL
# client tools on the host) and encrypts the resulting dump with GPG before
# it touches disk outside the container.
#
# Configuration (environment variables, all optional except in production):
#   BACKUP_DIR             Output directory for backups (default: ./backups)
#   BACKUP_ENCRYPT_KEY     GPG recipient (key ID, fingerprint, or email) to
#                          encrypt the dump with. Required in production —
#                          see app/config.py::production_guard(). Without it,
#                          this script stores an UNENCRYPTED dump and prints
#                          a loud warning (acceptable for local dev only).
#   BACKUP_RETENTION_DAYS  Delete backups older than this many days
#                          (default: 30; set to 0 to disable pruning)
#   DB_CONTAINER           Name of the running PostgreSQL container
#                          (default: auto-detected via `docker compose ps -q db`,
#                          falling back to "nak-district-planner-db-1")
#   POSTGRES_USER          DB user for pg_dump (default: read from .env, else "nak")
#   POSTGRES_DB            DB name for pg_dump (default: read from .env, else "nak_planner")
#
# Usage:
#   ./scripts/backup.sh
#   BACKUP_ENCRYPT_KEY=backup@example.com ./scripts/backup.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Pick up POSTGRES_USER/POSTGRES_DB from .env if not already set in the environment.
if [[ -f "$REPO_ROOT/.env" ]]; then
  POSTGRES_USER="${POSTGRES_USER:-$(grep -m1 '^POSTGRES_USER=' "$REPO_ROOT/.env" | cut -d= -f2-)}"
  POSTGRES_DB="${POSTGRES_DB:-$(grep -m1 '^POSTGRES_DB=' "$REPO_ROOT/.env" | cut -d= -f2-)}"
fi

BACKUP_DIR="${BACKUP_DIR:-$REPO_ROOT/backups}"
BACKUP_RETENTION_DAYS="${BACKUP_RETENTION_DAYS:-30}"
POSTGRES_USER="${POSTGRES_USER:-nak}"
POSTGRES_DB="${POSTGRES_DB:-nak_planner}"

resolve_container() {
  if [[ -n "${DB_CONTAINER:-}" ]]; then
    echo "$DB_CONTAINER"
    return
  fi
  local detected
  detected="$(cd "$REPO_ROOT" && docker compose ps -q db 2>/dev/null || true)"
  if [[ -n "$detected" ]]; then
    echo "$detected"
    return
  fi
  echo "nak-district-planner-db-1"
}

DB_CONTAINER="$(resolve_container)"

if ! docker exec "$DB_CONTAINER" true 2>/dev/null; then
  echo "ERROR: cannot reach PostgreSQL container '$DB_CONTAINER'." >&2
  echo "       Set DB_CONTAINER explicitly or ensure the stack is running (docker compose up -d)." >&2
  exit 1
fi

mkdir -p "$BACKUP_DIR"

timestamp="$(date -u +%Y%m%d_%H%M%S)"
dump_file="$BACKUP_DIR/${POSTGRES_DB}_${timestamp}.dump"

echo "==> Dumping database '$POSTGRES_DB' from container '$DB_CONTAINER'..."
docker exec "$DB_CONTAINER" pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Fc >"$dump_file"

if [[ -n "${BACKUP_ENCRYPT_KEY:-}" ]]; then
  echo "==> Encrypting backup for recipient '$BACKUP_ENCRYPT_KEY'..."
  gpg --batch --yes --trust-model always --encrypt --recipient "$BACKUP_ENCRYPT_KEY" \
    --output "${dump_file}.gpg" "$dump_file"
  rm -f "$dump_file"
  final_file="${dump_file}.gpg"
else
  echo "WARNING: BACKUP_ENCRYPT_KEY is not set — storing an UNENCRYPTED backup." >&2
  echo "         This is only acceptable for local development. Production startup" >&2
  echo "         is blocked by production_guard() until BACKUP_ENCRYPT_KEY is set." >&2
  final_file="$dump_file"
fi

if [[ "$BACKUP_RETENTION_DAYS" -gt 0 ]]; then
  echo "==> Pruning backups older than ${BACKUP_RETENTION_DAYS} days..."
  find "$BACKUP_DIR" -maxdepth 1 -name "${POSTGRES_DB}_*.dump*" -mtime "+${BACKUP_RETENTION_DAYS}" -print -delete
fi

echo "==> Backup complete: $final_file ($(du -h "$final_file" | cut -f1))"
