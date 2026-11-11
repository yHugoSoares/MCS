#set document(title: "NS TP2 - TCP Attacks", author: "PL1y")
#set page(margin: 2cm)
#set heading(numbering: "1.")
#set raw(theme: none)

#align(center)[#text(18pt)[NS TP2 -- TCP Attacks Lab]]
#align(center)[#text(11pt)[Task 1.2 (C SYN Flood) + Task 1.3 (SYN Cookies) -- UbuntuSR VM]]
#v(0.5em)

== Environment
- Host: macOS arm64, VMware Fusion VM `UbuntuSR` @ `192.168.153.137` (`seed`/`dees`, `aarch64`).
- Lab: `~/TP2_Labsetup` (from `Labsetup.zip`), `synflood.c` + patched `docker-compose.yml` (removed `iptables -I OUTPUT ...` line: `iptables v1.8.4 (legacy): can't initialize table filter` on this kernel; `inetd :23` only).
- Containers: `seed-attacker` (host net), `victim-10.9.0.5`, `user1-10.9.0.6`, `user2-10.9.0.7` on `net-10.9.0.0`.
- Build (VM, aarch64): `gcc -static -o volumes/synflood volumes/synflood.c` (guide p3-4; `-static` for Apple Silicon/aarch64, plain `gcc -o synflood synflood.c` on x86_64).

#figure(caption: [Screenshot 1 -- `docker ps` all Up + `ss -tln` :23 LISTEN on victim.])[
```bash
docker ps --format "{{.Names}}|{{.Status}}"
# user2-10.9.0.7|Up 5 seconds
# user1-10.9.0.6|Up 5 seconds
# victim-10.9.0.5|Up 5 seconds
# seed-attacker|Up 5 seconds
docker exec victim-10.9.0.5 ss -tln | head
# LISTEN 0 0 0.0.0.0:23 0.0.0.0:*
```]

== Task 1.2 -- C SYN Flood (cookies OFF)
Pre-config per guide p2-3:
```bash
docker exec victim-10.9.0.5 sysctl -w net.ipv4.tcp_syncookies=0
# net.ipv4.tcp_syncookies = 0
docker exec victim-10.9.0.5 sysctl -w net.ipv4.tcp_max_syn_backlog=128
docker exec victim-10.9.0.5 ip tcp_metrics flush
# NOTE: guide prints `ip tcp metrics flush`; real syntax is `ip tcp_metrics flush`
docker exec victim-10.9.0.5 sysctl net.ipv4.tcp_syncookies net.ipv4.tcp_max_syn_backlog
# net.ipv4.tcp_syncookies = 0
# net.ipv4.tcp_max_syn_backlog = 128
```

Attack + queue + legit client:
```bash
docker exec -d seed-attacker /volumes/synflood 10.9.0.5 23
docker exec seed-attacker ps aux | grep synflood
# root 13 98.0 0.0 840 568 ? Rs 0:01 /volumes/synflood 10.9.0.5 23
sleep 30
docker exec victim-10.9.0.5 ss -n state syn-recv sport = :23 | wc -l
# 98   (re-sample 97; ~128*3/4, 1/4 reserved for proven-dst, Note A p3)
time docker exec user1-10.9.0.6 timeout 10 telnet 10.9.0.5 23; echo TELNET_EXIT:$?
# TELNET_EXIT:124, 10.060s total -> hang/timeout = DoS confirmed
docker exec seed-attacker pkill -f synflood
```

#figure(caption: [Screenshot 2 -- Task 1.2: `ss ... | wc -l` ~= 98 + `telnet` exit 124 after 10s.])[
```
98
97
TELNET_EXIT:124
```]

Result: backlog saturated, legitimate `10.9.0.6 -> 10.9.0.5:23` starved.

== Task 1.3 -- SYN Cookie countermeasure (cookies ON)
```bash
docker exec victim-10.9.0.5 sysctl -w net.ipv4.tcp_syncookies=1
docker exec victim-10.9.0.5 sysctl net.ipv4.tcp_syncookies
# net.ipv4.tcp_syncookies = 1
docker exec -d seed-attacker /volumes/synflood 10.9.0.5 23
sleep 20
time docker exec user1-10.9.0.6 timeout 10 telnet 10.9.0.5 23; echo TELNET_EXIT:$?
# Trying 10.9.0.5...
# Connected to 10.9.0.5.
# Escape character is '^]'.
# Connection closed by foreign host.
# TELNET_EXIT:1, 0.115s total -> TCP handshake succeeds under flood
docker exec seed-attacker pkill -f synflood
docker exec victim-10.9.0.5 dmesg | grep -i -e "syn flood" -e cookie | tail
# [965.517222] TCP: request_sock_TCP: Possible SYN flooding on port 0.0.0.0:23. Sending cookies.
```

#figure(caption: [Screenshot 3 -- Task 1.3: `Connected to 10.9.0.5` in 0.1s + dmesg `Sending cookies`.])[
```
Trying 10.9.0.5...
Connected to 10.9.0.5.
TCP: request_sock_TCP: Possible SYN flooding on port 0.0.0.0:23. Sending cookies.
```]

Result: with cookies on, client connects despite active flood (non-interactive close after accept is expected without credentials; `Connected` proves mitigation).

== Task 1.1 (Python/Scapy) vs 1.2 (C)
- Python/Scapy: per-packet userspace overhead, socket creation + Python-level `rand` for src IP/port/seq, GIL; low pps. Fails to hold the queue because each `tcp_synack_retries=5` expiry frees a slot that the slow sender loses to the legit SYN; needs N parallel instances and smaller backlog to win (guide p3).
- C (`synflood.c`): tight `while(1)` loop, one `SOCK_RAW`+`IP_HDRINCL` `sendto` per SYN, `rand()` in C, spoofed src IP/port/seq, correct TCP checksum via pseudo-header; near line-rate pps at ~98% CPU. Fills backlog 128 faster than retransmit timeouts free it, starving legit SYNs. Same `ip tcp_metrics flush` caveat (proven-dst quarter, Note A p3) applies; restore `backlog=128` before comparing (guide p4).

== How SYN Cookies work
- Stateless: on SYN, server allocates no TCB/backlog slot; replies `SYN+ACK` with cryptographic ISN = `hash(saddr, daddr, sport, dport, secret, time)` encoding MSS/options.
- On final ACK, server recomputes ISN, checks `ack-1`, and only then creates the socket. Incomplete (spoofed) handshakes cost zero memory, so the queue cannot fill; legit clients connect (`Sending cookies` in dmesg). Trade-off: some TCP options degraded under attack.

== Screenshots checklist (paste into appendix)
1. `docker ps` (4 Up) + `ss -tln` :23 LISTEN.
2. Task 1.2: `sysctl` 0/128, `ps` synflood 98% CPU, `ss | wc -l` 98/97, `telnet` 124/10s.
3. Task 1.3: `sysctl` 1, `telnet` Connected/0.1s, `dmesg` Sending cookies.
4. `docker-compose.yml` diff (iptables line removed) + `gcc -static` BUILD_OK (optional, explains env fix).

== Conclusion / struggles
- `Labsetup.zip` in SR dir lacked `synflood.c`; used `~/Downloads/Labsetup.zip` version (correct `victim-10.9.0.5`/`user1-10.9.0.6` names + `sysctls: syncookies=0`).
- Stock compose `iptables ...` fails on UbuntuSR kernel (`can't initialize table filter`); containers exited(3) until line removed.
- Guide `ip tcp metrics flush` typo; use `ip tcp_metrics flush`.
- `ss` prints `Cannot open netlink socket` in containers but still counts; `netstat -tna | grep SYN_RECV` as fallback (guide p2-3).
- Suggest: fix typo, note Apple Silicon `-static` + VMware `iptables` workaround, state expected counts (~96 usable of 128).
