#!/usr/bin/env bash
# Restore a NAK District Planner PostgreSQL backup created by scripts/backup.sh.
#
# Decrypts (if needed), verifies archive integrity via `pg_restore --list`,
# and — unless --dry-run is given — restores into the running `db` container
# after an explicit confirmation prompt.
#
# Configuration (environment variables):
#   BACKUP_ENCRYPT_KEY   GPG key to decrypt a `.dump.gpg` backup. Not needed
#                        for plaintext `.dump` files.
#   DB_CONTAINER         Name of the running PostgreSQL container
#                        (default: auto-detected via `docker compose ps -q db`,
#                        falling back to "nak-district-planner-db-1")
#   POSTGRES_USER        DB user for pg_restore (default: read from .env, else "nak")
#   POSTGRES_DB          DB name for pg_restore (default: read from .env, else "nak_planner")
#
# Usage:
#   ./scripts/restore.sh backups/nak_planner_20260907_120000.dump.gpg [--dry-run] [--yes]

set -euo pipefail

usage() {
  echo "Usage: $0 <backup-file> [--dry-run] [--yes]" >&2
  exit 1
}

[[ $# -ge 1 ]] || usage

BACKUP_FILE="$1"
shift || true
DRY_RUN=0
ASSUME_YES=0
for arg in "$@"; do
  case "$arg" in
    --dry-run) DRY_RUN=1 ;;
    --yes) ASSUME_YES=1 ;;
    *) usage ;;
  esac
done

[[ -f "$BACKUP_FILE" ]] || { echo "ERROR: backup file not found: $BACKUP_FILE" >&2; exit 1; }

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

if [[ -f "$REPO_ROOT/.env" ]]; then
  POSTGRES_USER="${POSTGRES_USER:-$(grep -m1 '^POSTGRES_USER=' "$REPO_ROOT/.env" | cut -d= -f2-)}"
  POSTGRES_DB="${POSTGRES_DB:-$(grep -m1 '^POSTGRES_DB=' "$REPO_ROOT/.env" | cut -d= -f2-)}"
fi
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

WORKDIR="$(mktemp -d)"
trap 'rm -rf "$WORKDIR"; docker exec "$DB_CONTAINER" rm -f /tmp/restore.dump 2>/dev/null || true' EXIT

local_dump="$WORKDIR/restore.dump"

if [[ "$BACKUP_FILE" == *.gpg ]]; then
  echo "==> Decrypting $BACKUP_FILE..."
  gpg --batch --yes --output "$local_dump" --decrypt "$BACKUP_FILE"
else
  cp "$BACKUP_FILE" "$local_dump"
fi

echo "==> Copying dump into container '$DB_CONTAINER'..."
docker cp "$local_dump" "$DB_CONTAINER:/tmp/restore.dump"

echo "==> Verifying archive integrity (pg_restore --list)..."
if ! docker exec "$DB_CONTAINER" pg_restore --list /tmp/restore.dump >/dev/null; then
  echo "ERROR: archive is not a valid pg_restore dump — aborting, database left untouched." >&2
  exit 1
fi
echo "    OK — archive is readable."

if [[ "$DRY_RUN" -eq 1 ]]; then
  echo "==> Dry run complete. Would restore into database '$POSTGRES_DB' on container '$DB_CONTAINER'."
  exit 0
fi

if [[ "$ASSUME_YES" -ne 1 ]]; then
  echo "WARNING: this will DROP and recreate objects in database '$POSTGRES_DB' on container '$DB_CONTAINER'."
  read -r -p "Continue? [y/N] " confirm
  [[ "$confirm" =~ ^[Yy]$ ]] || { echo "Aborted."; exit 1; }
fi

echo "==> Restoring into '$POSTGRES_DB'..."
docker exec "$DB_CONTAINER" pg_restore -U "$POSTGRES_USER" -d "$POSTGRES_DB" --clean --if-exists /tmp/restore.dump

echo "==> Restore complete. Verify application health and data integrity before declaring success."
