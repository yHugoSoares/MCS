#!/usr/bin/env bash
# Proves the L3 path end to end, independently of the firewall engine.
#
#   client -> firewall (gateway) -> web
#
# Two questions answered separately:
#   1. does the packet actually reach the firewall?   (tcpdump on the firewall)
#   2. does it reach the service?                     (curl from the client)
#
# Before role 2's engine exists the FORWARD policy is DROP, so (1) passes and
# (2) fails. Run scripts/bootstrap-forward.sh to check (2) too.
source "$(dirname "$0")/lib.sh"

CAPTURE_DIR="$(cd "$(dirname "$0")/.." && pwd)/logs/captures"
mkdir -p "$CAPTURE_DIR"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
PCAP="$CAPTURE_DIR/pathcheck-$STAMP.txt"

printf '== 1. firewall reachable from client ==\n'
if compose exec -T client ping -c 2 -W 1 "$LAB_FW_SERVER_IP" >/dev/null 2>&1; then
    printf '  ok: client can route to the firewall far side (%s)\n' "$LAB_FW_SERVER_IP"
else
    printf '  FAIL: client cannot reach %s (routing/gateway problem)\n' "$LAB_FW_SERVER_IP"
    exit 1
fi

printf '== 2. observe the flow at the firewall ==\n'
( compose exec -T firewall timeout 8 tcpdump -i any -nn -c 6 \
      "host ${LAB_CLIENT_IP} and host ${LAB_WEB_IP}" >"$PCAP" 2>&1 ) &
capture_pid=$!
sleep 1

printf '== 3. request the protected service from the client ==\n'
if compose exec -T client curl -fsS -m 3 "http://${LAB_WEB_IP}/healthz.php" >/dev/null 2>&1; then
    printf '  ok: legitimate request served\n'
    delivered=1
else
    printf '  blocked: no answer from %s (expected while FORWARD policy = DROP)\n' "$LAB_WEB_IP"
    delivered=0
fi

wait "$capture_pid" || true
packets=$(grep -c 'IP ' "$PCAP" 2>/dev/null || true)
printf '  %s packets seen at the firewall (capture: %s)\n' "${packets:-0}" "${PCAP#"$(pwd)/"}"

if [ "${packets:-0}" -eq 0 ]; then
    printf '\nFAIL: traffic never reached the firewall. The firewall is not the gateway.\n'
    exit 1
fi

if [ "$delivered" -eq 0 ]; then
    printf '\nPath is correct but enforcement is closed (firewall engine not running yet).\n'
    printf 'To validate forwarding only: scripts/bootstrap-forward.sh\n'
    exit 2
fi

printf '\nOK: packets cross the firewall and the service answers.\n'
