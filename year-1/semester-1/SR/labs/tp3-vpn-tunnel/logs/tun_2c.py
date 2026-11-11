#!/usr/bin/env python3

import fcntl
import struct
import os
import sys
from scapy.all import *

TUNSETIFF = 0x400454ca
IFF_TUN   = 0x0001
IFF_TAP   = 0x0002
IFF_NO_PI = 0x1000

# Create the tun interface
tun = os.open("/dev/net/tun", os.O_RDWR)
ifr = struct.pack('16sH', b'myInterface%d', IFF_TUN | IFF_NO_PI)
ifname_bytes  = fcntl.ioctl(tun, TUNSETIFF, ifr)

# Get the interface name
ifname = ifname_bytes.decode('UTF-8')[:16].strip("\x00")

os.system("ip addr add 192.168.53.99/24 dev {}".format(ifname))
os.system("ip link set dev {} up".format(ifname))

print("Interface Name: {}".format(ifname), flush=True)

while True:
    packet = os.read(tun, 2048)
    if not packet:
        continue
    pkt = IP(packet)
    if pkt.version != 4:          # skip IPv6 link-local noise
        continue
    print("From tun ==>: {} --> {} | proto={} len={} id={} ttl={}".format(
        pkt.src, pkt.dst, pkt.proto, pkt.len, pkt.id, pkt.ttl), flush=True)
    if pkt.haslayer(ICMP):
        icmp = pkt[ICMP]
        print("   ICMP type={} code={} id={} seq={} payload={}B".format(
            icmp.type, icmp.code, icmp.id, icmp.seq, len(bytes(icmp.payload))), flush=True)
