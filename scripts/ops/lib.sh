# SPDX-FileCopyrightText: 2026 Stephan Strittmatter
# SPDX-License-Identifier: AGPL-3.0-only

# shellcheck shell=bash
# shellcheck disable=SC2034 # constants and flags are used by nakctl, which sources this file

# Shared helpers for scripts/ops/nakctl. Sourced, never executed directly.
#
# Test hooks (never needed in production):
#   NAKCTL_VALKEY_CLI   command used instead of `valkey-cli` inside the valkey
#                       container (word-split, e.g. "valkey-cli -p 6380")
#   NAKCTL_PSQL         command used instead of psql inside the db container

# Exit codes (documented in docs/operations/admin-scripts.md)
readonly EXIT_OK=0
readonly EXIT_FINDING=1
readonly EXIT_USAGE=2
readonly EXIT_ENV=3
readonly EXIT_ABORTED=4

OPS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$OPS_DIR/../.." && pwd)"
DEPLOY_DIR="${NAK_DEPLOY_DIR:-$REPO_ROOT}"
NAKOPS="$OPS_DIR/nakops.py"

YES=0
DRY_RUN=0
HELP=0
ARGS=()

# Celery (Kombu Redis transport) key names; see design.md, decision 2.
readonly CELERY_QUEUE_KEY="celery"
readonly CELERY_UNACKED_KEY="unacked"
readonly CELERY_UNACKED_INDEX_KEY="unacked_index"
readonly CELERY_RESULT_PATTERN="celery-task-meta-*"

if [[ -t 1 ]]; then
  C_RED=$'\e[31m' C_YELLOW=$'\e[33m' C_GREEN=$'\e[32m' C_BOLD=$'\e[1m' C_RESET=$'\e[0m'
else
  C_RED="" C_YELLOW="" C_GREEN="" C_BOLD="" C_RESET=""
fi

info() { printf '%s\n' "$*"; }
ok() { printf '%sOK%s %s\n' "$C_GREEN" "$C_RESET" "$*"; }
warn() { printf '%sWARNUNG:%s %s\n' "$C_YELLOW" "$C_RESET" "$*" >&2; }
finding() { printf '%sBEFUND:%s %s\n' "$C_YELLOW" "$C_RESET" "$*"; }
heading() { printf '\n%s== %s ==%s\n' "$C_BOLD" "$*" "$C_RESET"; }

# die <exit-code> <message>
die() {
  local code="$1"
  shift
  printf '%sFEHLER:%s %s\n' "$C_RED" "$C_RESET" "$*" >&2
  exit "$code"
}

# Split global flags (--yes/-y, --dry-run, --help/-h) from the remaining arguments (ARGS).
parse_common_flags() {
  ARGS=()
  local arg
  for arg in "$@"; do
    case "$arg" in
      -y | --yes) YES=1 ;;
      --dry-run) DRY_RUN=1 ;;
      -h | --help) HELP=1 ;;
      *) ARGS+=("$arg") ;;
    esac
  done
}

# require_value <option> <value> — fail with a usage error when a value is missing.
require_value() {
  [[ -n "${2:-}" && "${2:0:2}" != "--" ]] || die "$EXIT_USAGE" "$1 braucht einen Wert"
}

enter_deploy_dir() {
  [[ -d "$DEPLOY_DIR" ]] || die "$EXIT_ENV" "Deploy-Verzeichnis $DEPLOY_DIR fehlt"
  cd "$DEPLOY_DIR" || die "$EXIT_ENV" "kann nicht nach $DEPLOY_DIR wechseln"
}

# env_get <KEY> [file] — read one value without sourcing the file.
env_get() {
  local key="$1" file="${2:-$DEPLOY_DIR/.env}" value
  [[ -f "$file" ]] || return 0
  value="$(grep -m1 -E "^(export[[:space:]]+)?${key}=" "$file" | cut -d= -f2- || true)"
  value="${value%$'\r'}"
  if [[ ${#value} -ge 2 && ( "${value:0:1}" == '"' || "${value:0:1}" == "'" ) && "${value: -1}" == "${value:0:1}" ]]; then
    value="${value:1:${#value}-2}"
  fi
  printf '%s' "$value"
}

# env_set <KEY> <value> [file] — replace or append KEY=value, keeping file permissions.
env_set() {
  local key="$1" value="$2" file="${3:-$DEPLOY_DIR/.env}" tmp
  tmp="$(mktemp "${file}.XXXXXX")"
  if grep -q -E "^${key}=" "$file"; then
    awk -v k="$key" -v v="$value" 'BEGIN{done=0} $0 ~ "^"k"=" && !done {print k"="v; done=1; next} {print}' "$file" >"$tmp"
  else
    cat "$file" >"$tmp"
    printf '%s=%s\n' "$key" "$value" >>"$tmp"
  fi
  chmod --reference="$file" "$tmp" 2>/dev/null || chmod 600 "$tmp"
  mv "$tmp" "$file"
}

require_docker() {
  command -v docker >/dev/null 2>&1 || die "$EXIT_ENV" "docker ist nicht installiert"
  docker compose version >/dev/null 2>&1 || die "$EXIT_ENV" "docker compose ist nicht verfügbar"
}

require_python() {
  command -v python3 >/dev/null 2>&1 || die "$EXIT_ENV" "python3 ist nicht installiert"
}

compose() { docker compose "$@"; }

nakops() { python3 -I "$NAKOPS" "$@"; }

# service_running <service> — true when at least one container of it runs.
service_running() {
  [[ -n "$(compose ps --status running -q "$1" 2>/dev/null)" ]]
}

# valkey_cli <args...> — the password stays inside the container (REDISCLI_AUTH).
valkey_cli() {
  if [[ -n "${NAKCTL_VALKEY_CLI:-}" ]]; then
    # shellcheck disable=SC2086 # intentional word splitting of the test command
    $NAKCTL_VALKEY_CLI "$@"
    return
  fi
  # shellcheck disable=SC2016 # expanded inside the container, not here
  compose exec -T valkey sh -c 'REDISCLI_AUTH="$VALKEY_PASSWORD" exec valkey-cli --no-auth-warning "$@"' valkey-cli "$@"
}

# db_psql <args...> — psql as the database owner inside the db container; reads SQL from stdin.
db_psql() {
  if [[ -n "${NAKCTL_PSQL:-}" ]]; then
    # shellcheck disable=SC2086 # intentional word splitting of the test command
    $NAKCTL_PSQL -X -v ON_ERROR_STOP=1 "$@"
    return
  fi
  # shellcheck disable=SC2016 # expanded inside the container, not here
  compose exec -T db sh -c 'exec psql -X -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB" "$@"' psql "$@"
}

# confirm <summary> [word] — ask for explicit confirmation unless --yes was given.
confirm() {
  local summary="$1" word="${2:-ja}" answer
  ((YES)) && return 0
  if [[ ! -t 0 ]]; then
    die "$EXIT_ABORTED" "$summary — Bestätigung nötig: interaktiv ausführen oder --yes angeben"
  fi
  printf '%s\nZum Fortfahren "%s" eingeben: ' "$summary" "$word"
  read -r answer || answer=""
  if [[ "$answer" != "$word" ]]; then
    info "Abgebrochen, nichts geändert."
    exit "$EXIT_ABORTED"
  fi
}

# audit_log <message> — one line per executed change in logs/nakctl.log.
audit_log() {
  local log_dir="$DEPLOY_DIR/logs"
  mkdir -p "$log_dir"
  printf '%s user=%s %s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$(id -un 2>/dev/null || echo unknown)" "$*" \
    >>"$log_dir/nakctl.log"
}

# state_get/state_set — remembered values such as PREVIOUS_VERSION.
STATE_FILE="$DEPLOY_DIR/logs/nakctl.state"
state_get() { env_get "$1" "$STATE_FILE"; }
state_set() {
  mkdir -p "$(dirname "$STATE_FILE")"
  [[ -f "$STATE_FILE" ]] || install -m 600 /dev/null "$STATE_FILE"
  env_set "$1" "$2" "$STATE_FILE"
}

image_registry() {
  local registry
  registry="$(env_get IMAGE_REGISTRY)"
  printf '%s' "${IMAGE_REGISTRY:-${registry:-ghcr.io/stritti/nak-district-planner}}"
}

# Same default as scripts/backup.sh (which reads BACKUP_DIR only from the environment).
backup_dir() {
  printf '%s' "${BACKUP_DIR:-$REPO_ROOT/backups}"
}

app_db_name() {
  local name
  name="$(env_get POSTGRES_DB)"
  printf '%s' "${POSTGRES_DB:-${name:-nak_planner}}"
}

# Collect the worst exit code of several checks (0 ok < 1 finding < 3 environment).
WORST=0
record() {
  (($1 > WORST)) && WORST="$1"
  return 0
}
