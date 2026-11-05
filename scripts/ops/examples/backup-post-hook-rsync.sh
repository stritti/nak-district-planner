#!/usr/bin/env bash
# SPDX-FileCopyrightText: 2026 Stephan Strittmatter
# SPDX-License-Identifier: AGPL-3.0-only

# Example BACKUP_POST_HOOK for `nakctl backup create`: copy the encrypted
# database and role archives to another host with rsync over SSH.
#
# nakctl calls the hook with two arguments:
#   $1  path of the database archive (<db>_<timestamp>.dump.gpg)
#   $2  path of the role archive     (<db>_<timestamp>.roles.sql.gpg)
#
# Copy this file outside the repository (or keep it here), adjust the target,
# make it executable and owned by the operator (chmod 700), and set in .env:
#   BACKUP_POST_HOOK=/opt/nak/backup-offsite.sh
#
# Configuration (.env of the deploy directory, the environment, or edit below;
# nakctl passes OFFSITE_* values from .env to this hook):
#   OFFSITE_TARGET   rsync target, e.g. backup@backup.example.org:/srv/nak/
#   OFFSITE_SSH_KEY  SSH key for the transfer (default: ~/.ssh/id_ed25519)

set -euo pipefail

OFFSITE_TARGET="${OFFSITE_TARGET:?Set OFFSITE_TARGET, e.g. backup@backup.example.org:/srv/nak/}"
OFFSITE_SSH_KEY="${OFFSITE_SSH_KEY:-$HOME/.ssh/id_ed25519}"

(($# == 2)) || { echo "usage: $0 <dump-archive> <roles-archive>" >&2; exit 2; }

for archive in "$@"; do
  [[ "$archive" == *.gpg ]] || { echo "refusing to copy unencrypted archive: $archive" >&2; exit 1; }
done

rsync --archive --partial --chmod=F600 \
  -e "ssh -i $OFFSITE_SSH_KEY -o BatchMode=yes -o StrictHostKeyChecking=yes" \
  "$1" "$2" "$OFFSITE_TARGET"
echo "offsite copy done: $(basename "$1"), $(basename "$2")"
