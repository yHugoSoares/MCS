#!/usr/bin/env bash
# Container entrypoint for anything that is NOT the firewall.
#
# Docker's `internal: true` networks have no default route, so each host gets
# one pointed at the firewall. This script also keeps the container alive when
# it is started with `sleep infinity`.
set -euo pipefail

if [ -n "${GATEWAY:-}" ]; then
    # Wait for the network namespace to be configured (a few hundred ms at boot).
    for _ in $(seq 1 100); do
        if ip -4 route get "$GATEWAY" >/dev/null 2>&1; then
            break
        fi
        sleep 0.1
    done
    ip route replace default via "$GATEWAY"
fi

exec "$@"
