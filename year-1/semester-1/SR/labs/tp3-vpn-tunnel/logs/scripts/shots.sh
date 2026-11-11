#!/bin/bash
# Gera os transcritos usados nas "screenshots" do relatorio (output real do lab).
C=client-10.9.0.5
OUT=/tmp/out
mkdir -p $OUT

p() { echo; echo "seedvm:~\$ $*"; "$@" 2>&1; }

cleanup() {
  docker exec $C pkill -f tun_2c.py >/dev/null 2>&1
  docker exec $C pkill -f tun_2d.py >/dev/null 2>&1
  docker exec $C pkill -f tun_2d_garbage.py >/dev/null 2>&1
  docker exec $C ip link del myInterface0 >/dev/null 2>&1
}

# ---------- 2.c experimento 1 ----------
{
  cleanup
  p docker exec -d $C bash -c "python3 -u /volumes/tun_2c.py > /volumes/tun2c.log 2>&1"
  sleep 3
  p docker exec $C ip -br addr show myInterface0
  p docker exec $C ip route
  p docker exec $C ping -c 3 -W 1 192.168.53.1
  p docker exec $C cat /volumes/tun2c.log
  p docker exec $C ip -s link show myInterface0
} > $OUT/2c_ping.txt

# ---------- 2.c experimento 2 ----------
{
  p docker exec $C ip route get 192.168.60.5
  p docker exec $C wc -l /volumes/tun2c.log
  docker exec -d $C bash -c "ping -c 3 -W 1 192.168.60.5 > /volumes/ping60.log 2>&1"
  p docker exec $C timeout 5 tcpdump -ni eth0 icmp -c 3
  sleep 1
  p docker exec $C cat /volumes/ping60.log
  p docker exec $C wc -l /volumes/tun2c.log
} > $OUT/2c_eth0.txt

# ---------- 2.d experimento 1 ----------
{
  cleanup
  p docker exec -d $C bash -c "python3 -u /volumes/tun_2d.py > /volumes/tun2d.log 2>&1"
  sleep 3
  p docker exec $C ping -c 3 -W 1 192.168.53.1
  p docker exec $C cat /volumes/tun2d.log
  p docker exec $C ip -s link show myInterface0
} > $OUT/2d_reply.txt

# ---------- 2.d experimento 2 ----------
{
  cleanup
  p docker exec -d $C bash -c "python3 -u /volumes/tun_2d_garbage.py > /volumes/tun2d_garbage.log 2>&1"
  sleep 5
  p docker exec $C cat /volumes/tun2d_garbage.log
  p docker exec $C ping -c 2 -W 1 192.168.53.1
} > $OUT/2d_garbage.txt

cleanup
docker exec $C rm -f /volumes/ping60.log >/dev/null 2>&1
echo "done"
