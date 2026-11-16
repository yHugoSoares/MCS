# SR — Network Security

MSc in Cybersecurity, University of Minho, 2026/27.

Hands-on network attacks and defences, run against a local VM lab
(`UbuntuSR` under VMware Fusion, Docker-based topologies).

## Contents

```text
theory/                     lecture slides
labs/
├── tp1-packet-sniffing/    TP1 — Packet Sniffing and Spoofing (6h)
├── tp2-tcp-attacks/        TP2 — TCP Attacks (4h)
└── tp3-vpn-tunnel/         TP3 — VPN Tunnel (6h)
SR2627/                     TP4 — programmable firewall (submodule, own repo)
```

## Labs

| Lab | Folder                   | Work                                                     |
| --- | ------------------------ | -------------------------------------------------------- |
| TP1 | `tp1-packet-sniffing`    | Statement only — Scapy sniffing and spoofing             |
| TP2 | `tp2-tcp-attacks`        | Task 1.2 SYN flood (`logs/synflood.c`) and 1.3 SYN cookies |
| TP3 | `tp3-vpn-tunnel`         | TUN/TAP tunnel, sections 2.c and 2.d                     |
| TP4 | `SR2627`                 | Programmable firewall + attack monitoring (group project, submodule) |

## Build

The reports are written in Typst.

```sh
# TP2
cd labs/tp2-tcp-attacks
typst compile report.typ

# TP3 — also regenerates the figures from the captured transcripts
cd labs/tp3-vpn-tunnel/logs
make            # figures + ../report.pdf
```

`tp3-vpn-tunnel/logs/README.md` explains where the figures come from and how to replace
them with real screenshots.

## TP4 — programmable firewall

`SR2627/` is a git submodule pointing at
[yHugoSoares/SR2627](https://github.com/yHugoSoares/SR2627). Its `master` branch
holds the role-1 infrastructure (topology, targets, benign traffic); the
`full-work` branch holds the complete scaffold.

```sh
git submodule update --init year-1/semester-1/SR/SR2627   # first time
cd SR2627/lab && make up && make verify
```

## Theory

`theory/` holds the seven lecture decks:

- `SR2627_0_Apresentação_v02` — course presentation
- `NetSecurity01` — Introduction, Threats and Attacks
- `NetSecurity02-03` — Transport Layer Security (TLS)
- `NetSecurity04` — Security at the Transport Layer (TCP/UDP/QUIC)
- `NetSecurity05` — Network Layer Security (IP/ICMP + IPsec)
- `NetSecurity06` — Network Layer Security (VPNs + IPv6)
- `NetSecurity-07` — Routing Security

Re-sync with `python3 tools/elearning-sync/sync.py --course SR`.
