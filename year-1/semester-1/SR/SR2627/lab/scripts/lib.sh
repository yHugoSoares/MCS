#!/usr/bin/env bash
# Shared helpers, sourced by the scripts in this folder.
# Intentionally dependency-free: bash + iproute2 only.

set -euo pipefail

# Interface that owns a given IPv4 address (e.g. 10.9.0.254 -> eth0).
# Needed because Docker does not guarantee eth0/eth1/eth2 ordering when a
# container joins several networks.
iface_for_ip() {
    local ip="${1:?iface_for_ip: missing address}"
    ip -o -4 addr show | awk -v want="${ip}/" '$4 ~ "^" want {print $2; exit}'
}

# Fail with a clear message instead of a cryptic shell error.
die() {
    printf 'error: %s\n' "$*" >&2
    exit 1
}

# Make the scripts usable when called directly (not only through `make`).
_lab_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
if [ -z "${LAB_WEB_IP:-}" ] && [ -f "$_lab_root/.env" ]; then
    set -a
    # shellcheck disable=SC1091
    . "$_lab_root/.env"
    set +a
fi

# docker compose wrapper that always runs from lab/, whatever the caller's cwd.
compose() {
    docker compose --project-directory "$_lab_root" "$@"
}
