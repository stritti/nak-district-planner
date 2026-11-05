#!/usr/bin/env bash
# SPDX-FileCopyrightText: 2026 Stephan Strittmatter
# SPDX-License-Identifier: AGPL-3.0-only

# Install or update the deploy bundle of one release (compose files, .env templates,
# Traefik config, nakctl) without git. Verifies the SHA-256 checksum before it writes
# anything and never touches .env files, logs/ or backups/.
#
# Test hook (never needed in production):
#   NAK_INSTALL_BASE_URL   release download base (default: GitHub releases); https:// or file://

set -euo pipefail

readonly EXIT_OK=0
readonly EXIT_USAGE=2
readonly EXIT_ENV=3
readonly EXIT_ABORTED=4

readonly REPO_URL="https://github.com/stritti/nak-district-planner"
BASE_URL="${NAK_INSTALL_BASE_URL:-$REPO_URL/releases/download}"

version=""
dir="/opt/nak-district-planner"
bin_dir="/usr/local/bin"
link=1
pin=""
yes=0
dry_run=0

info() { printf '%s\n' "$*"; }
ok() { printf 'OK %s\n' "$*"; }
warn() { printf 'WARNUNG: %s\n' "$*" >&2; }
die() {
  local code="$1"
  shift
  printf 'FEHLER: %s\n' "$*" >&2
  exit "$code"
}

usage() {
  cat <<EOF
Aufruf: install.sh --version <version> [optionen]

Installiert das Deploy-Paket eines Releases (Compose-Dateien, .env-Vorlagen,
Traefik-Konfiguration, nakctl) ohne git oder lädt bei einer vorhandenen
Installation die neue Version ein. Die Prüfsumme wird geprüft, bevor etwas
geschrieben wird. .env-Dateien, logs/ und backups/ bleiben unberührt.

Optionen:
  --version <version>         Release, z. B. 1.8.0 (Pflicht)
  --dir <pfad>                Zielverzeichnis (Standard: /opt/nak-district-planner)
  --sha256 <prüfsumme>        erwartete SHA-256 des Pakets zusätzlich prüfen
  --bin-dir <pfad>            hier den Befehl nakctl anlegen (Standard: /usr/local/bin)
  --no-link                   keinen nakctl-Befehl anlegen
  --dry-run                   nur herunterladen, prüfen und anzeigen
  -y, --yes                   Update ohne Rückfrage
  -h, --help                  diese Hilfe

Exit-Codes: 0 ok, 2 Aufruf, 3 Umgebung/Prüfung, 4 abgebrochen

Beispiele:
  curl -fsSLO $REPO_URL/releases/download/v1.8.0/install.sh
  less install.sh
  sudo bash install.sh --version 1.8.0
  sudo /opt/nak-district-planner/scripts/ops/install.sh --version 1.9.0
EOF
}

require_value() {
  [[ -n "${2:-}" && "${2:0:2}" != "--" ]] || die "$EXIT_USAGE" "$1 braucht einen Wert"
}

while (($#)); do
  case "$1" in
    --version) require_value "$1" "${2:-}"; version="${2#v}"; shift 2 ;;
    --dir) require_value "$1" "${2:-}"; dir="${2%/}"; shift 2 ;;
    --sha256) require_value "$1" "${2:-}"; pin="${2,,}"; shift 2 ;;
    --bin-dir) require_value "$1" "${2:-}"; bin_dir="${2%/}"; shift 2 ;;
    --no-link) link=0; shift ;;
    --dry-run) dry_run=1; shift ;;
    -y | --yes) yes=1; shift ;;
    -h | --help) usage; exit "$EXIT_OK" ;;
    *) die "$EXIT_USAGE" "unbekannte Option: $1 (Hilfe: install.sh --help)" ;;
  esac
done

[[ -n "$version" ]] || die "$EXIT_USAGE" "--version fehlt (Hilfe: install.sh --help)"
[[ "$version" =~ ^[0-9]+\.[0-9]+\.[0-9]+(-[0-9A-Za-z.]+)?$ ]] ||
  die "$EXIT_USAGE" "ungültige Version: $version (erwartet z. B. 1.8.0)"
[[ -z "$pin" || "$pin" =~ ^[0-9a-f]{64}$ ]] || die "$EXIT_USAGE" "--sha256 erwartet 64 Hex-Zeichen"
safe_path='^/[A-Za-z0-9._/-]*$'
for path in "$dir" "$bin_dir"; do
  [[ "$path" =~ $safe_path && "/$path/" != *"/../"* && "$path" != "/" ]] ||
    die "$EXIT_USAGE" "ungültiger Pfad: $path (absolut, ohne Leerzeichen und ..)"
done
case "$BASE_URL" in
  https://* | file://*) ;;
  *) die "$EXIT_USAGE" "NAK_INSTALL_BASE_URL muss mit https:// beginnen" ;;
esac

for tool in curl tar gzip; do
  command -v "$tool" >/dev/null 2>&1 || die "$EXIT_ENV" "$tool fehlt"
done
if command -v sha256sum >/dev/null 2>&1; then
  sha256() { sha256sum "$1" | awk '{print $1}'; }
elif command -v shasum >/dev/null 2>&1; then
  sha256() { shasum -a 256 "$1" | awk '{print $1}'; }
else
  die "$EXIT_ENV" "sha256sum oder shasum fehlt"
fi

fetch() {
  local url="$1" out="$2"
  if [[ "$url" == https://* ]]; then
    curl --proto '=https' --tlsv1.2 -fsSL --retry 3 -o "$out" "$url"
  else
    curl -fsSL -o "$out" "$url"
  fi || die "$EXIT_ENV" "Download fehlgeschlagen: $url"
}

name="nak-district-planner-deploy-$version.tar.gz"
prefix="nak-district-planner-$version"
tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT

info "==> Lade v$version"
fetch "$BASE_URL/v$version/$name" "$tmp/$name"
fetch "$BASE_URL/v$version/SHA256SUMS" "$tmp/SHA256SUMS"

expected="$(awk -v n="$name" '$2 == n || $2 == "*" n {print tolower($1)}' "$tmp/SHA256SUMS")"
[[ "$expected" =~ ^[0-9a-f]{64}$ ]] || die "$EXIT_ENV" "SHA256SUMS enthält keine Prüfsumme für $name"
actual="$(sha256 "$tmp/$name")"
[[ "$actual" == "$expected" ]] || die "$EXIT_ENV" "Prüfsumme von $name stimmt nicht mit SHA256SUMS überein; nichts installiert"
if [[ -n "$pin" ]]; then
  [[ "$actual" == "$pin" ]] || die "$EXIT_ENV" "Prüfsumme von $name stimmt nicht mit --sha256 überein; nichts installiert"
fi
ok "Prüfsumme $actual"

# Only regular files and directories below the release prefix; no links, no "..".
while IFS= read -r line; do
  case "${line:0:1}" in
    - | d) ;;
    *) die "$EXIT_ENV" "Paket enthält einen unerlaubten Eintrag (Link oder Gerät)" ;;
  esac
done < <(tar -tvzf "$tmp/$name")
while IFS= read -r entry; do
  [[ "$entry" == "$prefix" || "$entry" == "$prefix/"* ]] || die "$EXIT_ENV" "Paket enthält einen Eintrag außerhalb von $prefix/"
  [[ "/$entry/" != *"/../"* ]] || die "$EXIT_ENV" "Paket enthält einen Pfad mit .."
done < <(tar -tzf "$tmp/$name")

mkdir "$tmp/x"
tar -xzf "$tmp/$name" -C "$tmp/x" --no-same-owner
src="$tmp/x/$prefix"
[[ -f "$src/MANIFEST" && -f "$src/VERSION" ]] || die "$EXIT_ENV" "Paket ohne MANIFEST oder VERSION"
[[ "$(cat "$src/VERSION")" == "$version" ]] || die "$EXIT_ENV" "Paket meldet eine andere Version als $version"

files=()
while IFS= read -r file; do
  [[ -n "$file" ]] || continue
  [[ "$file" =~ ^[A-Za-z0-9._][A-Za-z0-9._/-]*$ && "/$file/" != *"/../"* ]] || die "$EXIT_ENV" "MANIFEST enthält einen ungültigen Pfad"
  # Operator data is never part of the bundle.
  [[ ! "$file" =~ ^(\.env|\.env\.db|\.env\.keycloak|\.env\.keycloak-db)$ && ! "$file" =~ ^(logs|backups)/ ]] ||
    die "$EXIT_ENV" "MANIFEST nennt Betreiberdaten ($file)"
  [[ -f "$src/$file" ]] || die "$EXIT_ENV" "MANIFEST nennt $file, das im Paket fehlt"
  files+=("$file")
done <"$src/MANIFEST"

if [[ -e "$dir/.git" ]]; then
  die "$EXIT_ENV" "$dir ist ein git-Checkout; dort mit 'git fetch --tags && git checkout v$version' aktualisieren"
fi
mode="install"
if [[ -f "$dir/VERSION" && -f "$dir/MANIFEST" ]]; then
  mode="update"
  current="$(head -n1 "$dir/VERSION")"
  info "Update der Installation in $dir: ${current:-?} → $version"
elif [[ -d "$dir" && -n "$(ls -A "$dir")" ]]; then
  die "$EXIT_ENV" "$dir ist nicht leer und keine Installation dieses Pakets"
else
  info "Neuinstallation in $dir"
fi

if ((dry_run)); then
  if ((link)); then
    info "--dry-run: würde ${#files[@]} Dateien nach $dir schreiben und $bin_dir/nakctl anlegen."
  else
    info "--dry-run: würde ${#files[@]} Dateien nach $dir schreiben."
  fi
  exit "$EXIT_OK"
fi
if [[ "$mode" == "update" ]] && ((!yes)); then
  [[ -t 0 ]] || die "$EXIT_ABORTED" "Update braucht eine Bestätigung: mit --yes erneut aufrufen"
  read -r -p "Dateien in $dir durch v$version ersetzen? .env und Daten bleiben. [ja/N] " answer
  [[ "$answer" == "ja" ]] || die "$EXIT_ABORTED" "abgebrochen"
fi

mkdir -p "$dir"
for file in "${files[@]}"; do
  target="$dir/$file"
  mkdir -p "$(dirname "$target")"
  if [[ -x "$src/$file" ]]; then perm=0755; else perm=0644; fi
  install -m "$perm" "$src/$file" "$target.new.$$"
  mv -f "$target.new.$$" "$target"
done
ok "${#files[@]} Dateien in $dir"

if ((link)); then
  wrapper="$bin_dir/nakctl"
  if [[ -e "$wrapper" ]] && ! grep -q '^# nakctl wrapper (install.sh)$' "$wrapper" 2>/dev/null; then
    warn "$wrapper existiert und stammt nicht von install.sh; bleibt unverändert"
  elif [[ -d "$bin_dir" && -w "$bin_dir" ]]; then
    printf '#!/bin/sh\n# nakctl wrapper (install.sh)\nexec "%s/scripts/ops/nakctl" "$@"\n' "$dir" >"$wrapper.new.$$"
    chmod 0755 "$wrapper.new.$$"
    mv -f "$wrapper.new.$$" "$wrapper"
    ok "Befehl $wrapper"
  else
    warn "$bin_dir nicht beschreibbar; nakctl als $dir/scripts/ops/nakctl aufrufen"
  fi
fi

if [[ "$mode" == "install" ]]; then
  cat <<EOF

Nächste Schritte:
  cd $dir
  scripts/ops/nakctl setup init --app-host <APP_HOST> --auth-host <AUTH_HOST> --version $version
  scripts/ops/nakctl doctor --skip-checks
EOF
else
  cat <<EOF

Nächster Schritt (Backup, Images, Migration, Neustart):
  cd $dir && scripts/ops/nakctl deploy update $version
EOF
fi
