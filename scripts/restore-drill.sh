#!/usr/bin/env bash
# SPDX-FileCopyrightText: 2026 Stephan Strittmatter
# SPDX-License-Identifier: AGPL-3.0-only

set -euo pipefail

readonly POSTGRES_IMAGE="${RESTORE_DRILL_POSTGRES_IMAGE:-postgres:18-alpine}"
readonly POSTGRES_USER="${RESTORE_DRILL_POSTGRES_USER:-nak_planner}"
readonly POSTGRES_PASSWORD="${RESTORE_DRILL_POSTGRES_PASSWORD:-restore-drill-only}"
readonly POSTGRES_DB="${RESTORE_DRILL_POSTGRES_DB:-nak_planner}"
readonly DRILL_ID="${GITHUB_RUN_ID:-local}-$$"
readonly SOURCE_CONTAINER="nak-restore-source-${DRILL_ID}"
readonly TARGET_CONTAINER="nak-restore-target-${DRILL_ID}"
readonly WORK_DIR="$(mktemp -d)"
readonly BACKUP_DIR="${WORK_DIR}/backups"
readonly GNUPGHOME="${WORK_DIR}/gnupg"

export GNUPGHOME

cleanup() {
  docker rm -f "$SOURCE_CONTAINER" "$TARGET_CONTAINER" >/dev/null 2>&1 || true
  rm -rf "$WORK_DIR"
}
trap cleanup EXIT

log() {
  printf '[restore-drill] %s\n' "$*"
}

start_database() {
  local container="$1"

  docker run --rm -d \
    --name "$container" \
    -e "POSTGRES_USER=${POSTGRES_USER}" \
    -e "POSTGRES_PASSWORD=${POSTGRES_PASSWORD}" \
    -e "POSTGRES_DB=${POSTGRES_DB}" \
    "$POSTGRES_IMAGE" >/dev/null

  for _ in $(seq 1 30); do
    if docker exec "$container" psql \
      -U "$POSTGRES_USER" \
      -d "$POSTGRES_DB" \
      -Atqc 'SELECT 1' >/dev/null 2>&1; then
      return 0
    fi
    sleep 1
  done

  log "database ${POSTGRES_DB} in container ${container} did not become ready"
  docker logs "$container" >&2 || true
  return 1
}

create_probe_data() {
  docker exec -i "$SOURCE_CONTAINER" psql \
    -v ON_ERROR_STOP=1 \
    -U "$POSTGRES_USER" \
    -d "$POSTGRES_DB" <<'SQL'
CREATE TABLE restore_drill_probe (
    id integer PRIMARY KEY,
    payload text NOT NULL
);
INSERT INTO restore_drill_probe (id, payload)
VALUES (1, 'restore-drill-original');
SQL
}

generate_ephemeral_gpg_key() {
  mkdir -p "$GNUPGHOME"
  chmod 700 "$GNUPGHOME"

  gpg --batch --passphrase '' \
    --quick-generate-key 'NAK Restore Drill <restore-drill@invalid.local>' default default never \
    >/dev/null 2>&1

  gpg --batch --with-colons --list-keys \
    | awk -F: '$1 == "fpr" { print $10; exit }'
}

create_encrypted_backup() {
  local recipient="$1"

  mkdir -p "$BACKUP_DIR"
  env \
    BACKUP_DIR="$BACKUP_DIR" \
    BACKUP_ENCRYPT_KEY="$recipient" \
    BACKUP_RETENTION_DAYS=1 \
    DB_CONTAINER="$SOURCE_CONTAINER" \
    POSTGRES_USER="$POSTGRES_USER" \
    POSTGRES_DB="$POSTGRES_DB" \
    bash ./scripts/backup.sh >/dev/null

  find "$BACKUP_DIR" -maxdepth 1 -type f -name '*.dump.gpg' -print -quit
}

seed_target_with_conflicting_data() {
  docker exec -i "$TARGET_CONTAINER" psql \
    -v ON_ERROR_STOP=1 \
    -U "$POSTGRES_USER" \
    -d "$POSTGRES_DB" <<'SQL'
CREATE TABLE restore_drill_probe (
    id integer PRIMARY KEY,
    payload text NOT NULL
);
INSERT INTO restore_drill_probe (id, payload)
VALUES (1, 'restore-drill-target-before-restore');
SQL
}

run_restore() {
  local backup_file="$1"

  env \
    DB_CONTAINER="$TARGET_CONTAINER" \
    POSTGRES_USER="$POSTGRES_USER" \
    POSTGRES_DB="$POSTGRES_DB" \
    bash ./scripts/restore.sh "$backup_file" --dry-run --yes >/dev/null

  env \
    DB_CONTAINER="$TARGET_CONTAINER" \
    POSTGRES_USER="$POSTGRES_USER" \
    POSTGRES_DB="$POSTGRES_DB" \
    bash ./scripts/restore.sh "$backup_file" --yes >/dev/null
}

assert_restored_data() {
  local payload
  payload="$(docker exec "$TARGET_CONTAINER" psql \
    -U "$POSTGRES_USER" \
    -d "$POSTGRES_DB" \
    -Atc 'SELECT payload FROM restore_drill_probe WHERE id = 1')"

  if [[ "$payload" != 'restore-drill-original' ]]; then
    log "restored payload mismatch: ${payload}"
    return 1
  fi
}

assert_corrupt_archive_is_rejected_without_changes() {
  local encrypted_backup="$1"
  local plain_backup="${WORK_DIR}/valid.dump"
  local corrupt_backup="${WORK_DIR}/corrupt.dump"
  local before after

  gpg --batch --quiet --output "$plain_backup" --decrypt "$encrypted_backup"
  head -c 64 "$plain_backup" > "$corrupt_backup"

  before="$(docker exec "$TARGET_CONTAINER" psql \
    -U "$POSTGRES_USER" \
    -d "$POSTGRES_DB" \
    -Atc 'SELECT payload FROM restore_drill_probe WHERE id = 1')"

  if env \
    DB_CONTAINER="$TARGET_CONTAINER" \
    POSTGRES_USER="$POSTGRES_USER" \
    POSTGRES_DB="$POSTGRES_DB" \
      bash ./scripts/restore.sh "$corrupt_backup" --dry-run --yes >/dev/null 2>&1; then
    log 'corrupt archive was unexpectedly accepted'
    return 1
  fi

  after="$(docker exec "$TARGET_CONTAINER" psql \
    -U "$POSTGRES_USER" \
    -d "$POSTGRES_DB" \
    -Atc 'SELECT payload FROM restore_drill_probe WHERE id = 1')"

  if [[ "$before" != "$after" ]]; then
    log 'target data changed after rejected corrupt archive'
    return 1
  fi
}

main() {
  local recipient backup_file

  log 'starting isolated source database'
  start_database "$SOURCE_CONTAINER"
  create_probe_data

  log 'creating encrypted backup'
  recipient="$(generate_ephemeral_gpg_key)"
  backup_file="$(create_encrypted_backup "$recipient")"
  if [[ -z "$backup_file" || ! -f "$backup_file" ]]; then
    log 'encrypted backup was not created'
    return 1
  fi

  log 'stopping source database before restore'
  docker rm -f "$SOURCE_CONTAINER" >/dev/null

  log 'starting independent restore target'
  start_database "$TARGET_CONTAINER"
  seed_target_with_conflicting_data

  log 'validating and restoring backup'
  run_restore "$backup_file"
  assert_restored_data

  log 'verifying corrupt archives fail before changing target data'
  assert_corrupt_archive_is_rejected_without_changes "$backup_file"

  log 'restore drill completed successfully'
}

main "$@"
