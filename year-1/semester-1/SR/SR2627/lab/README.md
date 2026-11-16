# TP4 lab - task 1 (infrastructure)

Scope: the three deliverables of *Arquiteto de Infraestrutura* — the topology
with the firewall as mandatory gateway, the protected targets, and the benign
traffic generator. Runs with Docker Compose on macOS (arm64) and Linux
(x86_64/arm64); all images are multi-arch.

```text
 client_lan 10.9.0.0/24                    server_lan 10.9.1.0/24
 ┌────────────┐  ┌────────────┐             ┌────────────┐  ┌────────────┐
 │ attacker   │  │ client     │             │ web        │  │ db         │
 │ 10.9.0.2   │  │ 10.9.0.3   │             │ 10.9.1.2   │  │ 10.9.1.3   │
 └─────┬──────┘  └─────┬──────┘             └─────┬──────┘  └─────┬──────┘
       │   gateway     │   gateway                │   gateway     │
       └───────────────┴──────────► firewall ◄────┴───────────────┘
                        10.9.0.254 │ 10.9.1.254
```

Every packet between zones is routed by the firewall container. Each host gets
an explicit `default via 10.9.0.254` / `10.9.1.254` and the Docker bridge
gateway (`10.9.x.1`) is blackholed, so there is no other way out
(`scripts/net-init.sh`). No service is published to the host.

> **Do not set `internal: true` on these networks.** Docker 28+ implements it
> with a `DOCKER-INTERNAL` netfilter rule that drops any frame entering the
> bridge whose destination IP is outside the bridge subnet
> (`iifname br-... ip daddr != 10.9.0.0/24 drop`). Routed traffic to `10.9.1.x`
> enters `client_lan` with daddr `10.9.1.2`, so it is dropped before it reaches
> the firewall. The route + blackhole above achieves the same isolation without
> breaking the topology.

## Quick start

```bash
cd lab
make up          # build and start
make verify      # capture on the firewall while the client requests the web app
make baseline    # benign HTTP + ping traffic, 1/s, JSONL log
make stop-baseline
```

`make verify` must report packets seen **at the firewall** and a `200` from the
protected service: that is the proof that the firewall is on the path.

## Addressing

| Host | Container | Address | Purpose |
| --- | --- | --- | --- |
| attacker | `attacker` | 10.9.0.2 | attack host (tasks 3/4), `NET_ADMIN`+`NET_RAW` |
| client | `client` | 10.9.0.3 | benign user, runs `traffic/legit_client.py` |
| firewall | `firewall` | 10.9.0.254 / 10.9.1.254 | gateway, `ip_forward=1` |
| web | `web` | 10.9.1.2 | PHP/Apache, intentionally vulnerable |
| db | `db` | 10.9.1.3 | MariaDB 11, `labdb` |

Pinned MACs: attacker `02:42:0a:09:00:02`, client `02:42:0a:09:00:03`.

`NET_ADMIN` is granted to `client` and `web` for one reason only: programming
the default route towards the firewall requires it. Nothing else uses it.

## What this branch does not contain

Packet interception, decisions and logging (task 2), attack scripts (tasks 3/4)
and the monitoring stack (task 5) live on `main`, together with the full plan
(`docs/plan/01-infra.md`). Here the firewall only forwards — task 2 replaces its
`sleep infinity` command with the engine.

## Layout

```text
lab/
├── docker-compose.yml     5 services, 2 zones
├── .env                   addresses, MACs, database credentials
├── Makefile               up/down/verify/baseline/trial/logs
├── images/base/           debian:12 + python3 (attacker/client/firewall)
├── images/web/            php:8.2-apache + mysqli
├── web/                   vulnerable app (SQLi sinks) - attack target
├── db/init.sql            schema + seed data
├── traffic/legit_client.py benign HTTP + ICMP generator, JSONL + summary
└── scripts/               net-init (default route), lib, verify-path
```

## Common problems

| Symptom | Cause / fix |
| --- | --- |
| client cannot reach the firewall | default route lost: `docker compose restart client` |
| web unhealthy | `make logs F=db`; schema loads only on an empty volume: `make reset` |
| `make verify` sees 0 packets | firewall is not the gateway: `docker compose exec client ip route` |
| containers start with unexpected IPs/MACs | stale network: `docker compose down && docker network rm sr-tp4_client_lan sr-tp4_server_lan` |
| cross-zone traffic dies in `DOCKER-INTERNAL` | someone re-added `internal: true`, see the warning above |
| arm64 host pulls amd64 images | only add multi-arch images |

## Safety

Everything stays inside the two lab networks; `make clean` removes
containers, networks and the database volume. Attacks must never leave
`10.9.0.0/24` / `10.9.1.0/24`.
