#!/bin/sh
# SPDX-FileCopyrightText: 2026 Stephan Strittmatter
# SPDX-License-Identifier: AGPL-3.0-only

# Writes one `set_real_ip_from` per network in NGINX_REAL_IP_FROM (space or
# comma separated). Only these peers may set the client IP via X-Forwarded-For.
# Run by the official nginx image entrypoint from /docker-entrypoint.d/.
set -eu

networks="${NGINX_REAL_IP_FROM:-127.0.0.1/32 172.16.0.0/12}"
out=/etc/nginx/conf.d/real-ip-from.conf

: > "$out"
for net in $(echo "$networks" | tr ',' ' '); do
    case "$net" in
        *[!0-9A-Fa-f.:/]*) echo "invalid NGINX_REAL_IP_FROM entry: $net" >&2; exit 1 ;;
    esac
    echo "set_real_ip_from $net;" >> "$out"
done
