#!/usr/bin/env bash
# Restore a NAK District Planner PostgreSQL backup created by scripts/backup.sh.
#
# Decrypts (if needed), validates archive integrity by restoring into a
# disposable database, and — unless --dry-run is given — restores into the
# running `db` container after stopping application writers and an explicit
# confirmation prompt.
#
# Configuration (environment variables):
#   BACKUP_ENCRYPT_KEY   GPG key to decrypt a `.dump.gpg` backup. Not needed
#                        for plaintext `.dump` files.
#   DB_CONTAINER         Name of the running PostgreSQL container
#                        (default: auto-detected via `docker compose ps -q db`,
#                        falling back to "nak-district-planner-db-1")
#   POSTGRES_USER        DB user for pg_restore (default: read from .env, else "nak")
#   POSTGRES_DB          DB name for pg_restore (default: read from .env, else "nak_planner")
#   COMPOSE_PROJECT_NAME Docker Compose project name (default: directory name)
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

# Docker Compose project name (used for service control)
COMPOSE_PROJECT_NAME="${COMPOSE_PROJECT_NAME:-$(basename "$REPO_ROOT")}"

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

# Validate by restoring into a disposable database (validates TOC + all data blocks)
validate_dump() {
  local validate_db="${POSTGRES_DB}_validate_$(date -u +%Y%m%d_%H%M%S)"
  echo "==> Validating archive integrity (full restore into disposable database '$validate_db')..."
  
  # Create validation database
  docker exec "$DB_CONTAINER" psql -U "$POSTGRES_USER" -d postgres -c "CREATE DATABASE \"$validate_db\";" >/dev/null
  
  # Restore into validation database — this validates TOC AND all data blocks
  if ! docker exec "$DB_CONTAINER" pg_restore -U "$POSTGRES_USER" -d "$validate_db" --clean --if-exists /tmp/restore.dump >/dev/null 2>&1; then
    echo "ERROR: archive validation failed — dump appears corrupt or incomplete." >&2
    docker exec "$DB_CONTAINER" psql -U "$POSTGRES_USER" -d postgres -c "DROP DATABASE IF EXISTS \"$validate_db\";" >/dev/null 2>&1 || true
    return 1
  fi
  
  # Clean up validation database
  docker exec "$DB_CONTAINER" psql -U "$POSTGRES_USER" -d postgres -c "DROP DATABASE \"$validate_db\";" >/dev/null
  echo "    OK — archive is fully valid (TOC and data blocks)."
  return 0
}

if ! validate_dump; then
  exit 1
fi

if [[ "$DRY_RUN" -eq 1 ]]; then
  echo "==> Dry run complete. Would restore into database '$POSTGRES_DB' on container '$DB_CONTAINER'."
  exit 0
fi

# Stop application writers (backend, worker) to prevent conflicts during restore
stop_app_writers() {
  echo "==> Stopping application writers (backend, worker)..."
  cd "$REPO_ROOT"
  docker compose stop backend worker 2>/dev/null || true
  # Wait for connections to drain
  sleep 2
}

start_app_writers() {
  echo "==> Starting application writers (backend, worker)..."
  cd "$REPO_ROOT"
  docker compose start backend worker
  # Wait for health checks
  echo "==> Waiting for services to become healthy..."
  local max_wait=60
  local waited=0
  while [[ $waited -lt $max_wait ]]; do
    if docker compose ps backend worker 2>/dev/null | grep -q "healthy"; then
      echo "    Services healthy."
      return 0
    fi
    sleep 2
    waited=$((waited + 2))
  done
  echo "WARNING: Services did not report healthy within ${max_wait}s — check manually." >&2
}

if [[ "$ASSUME_YES" -ne 1 ]]; then
  echo "WARNING: this will STOP backend/worker, DROP and recreate objects in database '$POSTGRES_DB' on container '$DB_CONTAINER', then RESTART backend/worker."
  read -r -p "Continue? [y/N] " confirm
  [[ "$confirm" =~ ^[Yy]$ ]] || { echo "Aborted."; exit 1; }
fi

stop_app_writers

echo "==> Restoring into '$POSTGRES_DB'..."
if ! docker exec "$DB_CONTAINER" pg_restore -U "$POSTGRES_USER" -d "$POSTGRES_DB" --clean --if-exists /tmp/restore.dump; then
  echo "ERROR: restore failed — database may be in inconsistent state." >&2
  start_app_writers
  exit 1
fi

start_app_writers

echo "==> Restore complete. Verify application health and data integrity before declaring success."