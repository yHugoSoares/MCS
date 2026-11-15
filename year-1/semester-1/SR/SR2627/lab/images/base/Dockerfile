# Common base image for firewall, attacker and client.
# Multi-arch on purpose: debian:12-slim resolves to arm64 on Apple Silicon and
# to amd64 on x86_64 hosts, so the same files run on macOS and Linux.
FROM debian:12-slim

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

RUN apt-get update && apt-get install -y --no-install-recommends \
        bash ca-certificates curl wget jq \
        iproute2 iputils-ping traceroute tcpdump conntrack \
        netcat-openbsd socat dnsutils \
        iptables nftables \
        procps psmisc vim-tiny less \
        python3 python3-pip \
        nmap hping3 dnsmasq \
    && rm -rf /var/lib/apt/lists/*

# Scapy drives most of the L3/L4 attack scripts (roles 3/4) and is handy for
# firewall prototyping. Pinned for reproducible evidence.
RUN python3 -m pip install --break-system-packages "scapy==2.6.1"

WORKDIR /opt
CMD ["sleep", "infinity"]
