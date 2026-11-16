#!/usr/bin/env bash
# Container entrypoint for anything that is NOT the firewall.
#
# The firewall must be the only way out of the zone. Docker gives every
# container a default route via the bridge gateway (10.9.x.1, the VM host), so:
#
#   1. remember that gateway,
#   2. point the default route at the firewall instead,
#   3. blackhole the bridge gateway so nothing can sneak back to the host,
#   4. keep the container alive when started with `sleep infinity`.
#
# (The zone networks are not `internal: true`: Docker 28+ then drops routed
# frames whose destination leaves the bridge subnet, which breaks the
# firewall-as-router topology.)
set -euo pipefail

if [ -n "${GATEWAY:-}" ]; then
    for _ in $(seq 1 100); do
        if ip -4 route get "$GATEWAY" >/dev/null 2>&1; then
            break
        fi
        sleep 0.1
    done

    bridge_gw="$(ip -4 route show default 2>/dev/null | awk '{for (i = 1; i < NF; i++) if ($i == "via") print $(i + 1)}' | head -n1)"
    ip route replace default via "$GATEWAY"

    if [ -n "$bridge_gw" ] && [ "$bridge_gw" != "$GATEWAY" ]; then
        ip route replace blackhole "$bridge_gw/32" || true
        echo "net-init: default via $GATEWAY, $bridge_gw blackholed" >&2
    else
        echo "net-init: default via $GATEWAY" >&2
    fi
fi

exec "$@"
