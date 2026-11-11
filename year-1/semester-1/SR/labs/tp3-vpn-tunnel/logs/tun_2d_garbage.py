#!/usr/bin/env python3

import fcntl
import struct
import os
import time
from scapy.all import *

TUNSETIFF = 0x400454ca
IFF_TUN   = 0x0001
IFF_TAP   = 0x0002
IFF_NO_PI = 0x1000

tun = os.open("/dev/net/tun", os.O_RDWR)
ifr = struct.pack('16sH', b'myInterface%d', IFF_TUN | IFF_NO_PI)
ifname = fcntl.ioctl(tun, TUNSETIFF, ifr).decode('UTF-8')[:16].strip("\x00")

os.system("ip addr add 192.168.53.99/24 dev {}".format(ifname))
os.system("ip link set dev {} up".format(ifname))
print("Interface Name: {}".format(ifname), flush=True)
time.sleep(1)

data = b"THIS IS NOT AN IP PACKET"
try:
    os.write(tun, data)
    print("Wrote {} bytes to {}".format(len(data), ifname), flush=True)
except OSError as e:
    print("os.write({} bytes) -> OSError: {}".format(len(data), e), flush=True)

time.sleep(1)
print("--- ip -s link show", flush=True)
os.system("ip -s link show {}".format(ifname))

time.sleep(600)
