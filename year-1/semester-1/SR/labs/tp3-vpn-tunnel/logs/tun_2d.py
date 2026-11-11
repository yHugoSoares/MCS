#!/usr/bin/env python3

import fcntl
import struct
import os
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
    if pkt.version != 4:
        continue
    print("From tun ==>: {} --> {} proto={}".format(pkt.src, pkt.dst, pkt.proto), flush=True)

    if pkt.haslayer(ICMP) and pkt[ICMP].type == 8:
        icmp = pkt[ICMP]
        reply = IP(src=pkt.dst, dst=pkt.src) / \
                ICMP(type=0, id=icmp.id, seq=icmp.seq) / icmp.payload
        reply = IP(bytes(reply))          # rebuild -> correct len + checksums
        os.write(tun, bytes(reply))       # inject into the kernel
        print("   wrote echo reply {} --> {}".format(reply.src, reply.dst), flush=True)
