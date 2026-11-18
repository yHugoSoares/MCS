#!/usr/bin/env python3
"""Q3.a - DSA verification for the two signatures in the assignment.

H(M) = int(SHA-1(M)) mod q, as specified.  SHA-1 is used here only because the
exercise defines it; it is not a recommendation.

Usage: python3 q3a_dsa_verify.py
"""

from __future__ import annotations

import hashlib

# Global public-key components (PU_G).
P = int(
    "90d5e9facf54c404d5056469a3e7c7e425f93ed258f04a4b6217eabd9aa3acaacadb4059ef50fdf63a"
    "d42f8fad2857ee8f3f537c0628608f630342071b30724a94f88feb5faafd30a72221984f057749c0e"
    "8782e4492a6293c9e52e566c5222c5aef569098d1f501a2375ac07ee32725c4fb15f77c33a58f17fe"
    "4bd96b49a8bb",
    16,
)
Q = int("8b6bd7869151052c5de1d9e9771ff8a07b6d674b", 16)
G = int(
    "5b8b967cb90f9b488755a40b9831a981ee9a5486a3afd96ad7f8b86e35b8116c5dda04d4bfc2a7044"
    "fcea37f723e6406730c649e753e23c257e112bad0a9275317b433ec4de2cdc28c2d2c21c90008734e"
    "abecca0d60d490b02ab458f25d4f83aab06fcacba327b158aa0fe43754641dbfcf12b01952d30b1770"
    "ba4e5b1c4a33",
    16,
)

# Signer's public key.
Y = int(
    "466b1cbd3c016447d484c171e67d171a2ddb296b6546f1e0c0ebc47fc3d02217dc25b3dc34d3bf6ea4"
    "1ffd25d04bc47f6880a07e663ab0eb8924193ef2f90b46d76ed3faeee44684f13a676afdacd0f8216"
    "2f81ca210b3bc1914b8ef78ab531c5b7d5a44b984b6f23d9487290a6515116105617f0b5661c0d14f"
    "16da0d77c31f",
    16,
)

# The two signed messages and their signatures.
MESSAGE_1 = "TRANSFER 500 EUR TO ACCOUNT PT50-0001"
MESSAGE_2 = "TRANSFER 20 EUR TO ACCOUNT PT50-0002"
R = int("4b14d71b39ae81b4110c93f0d34930e041ec5c94", 16)
S1 = int("58f765a04b4aaa239c1e34ff7c13066dea00ea8d", 16)
S2 = int("81cc418f55b266a5cb4965c0d9321e1831ac03da", 16)


def hash_to_int(message: str) -> int:
    digest = hashlib.sha1(message.encode("utf-8")).digest()
    return int.from_bytes(digest, "big") % Q


def verify(message: str, r: int, s: int) -> bool:
    """DSA verification: v == r, with v = ((g^u1 * y^u2 mod p) mod q)."""
    if not (0 < r < Q and 0 < s < Q):
        return False
    h = hash_to_int(message)
    w = pow(s, -1, Q)
    u1 = (h * w) % Q
    u2 = (r * w) % Q
    v = (pow(G, u1, P) * pow(Y, u2, P) % P) % Q
    return v == r


def main() -> None:
    print(f"p: {P.bit_length()} bits, q: {Q.bit_length()} bits")
    print(f"r = {hex(R)}")
    print(f"H(M1) = {hex(hash_to_int(MESSAGE_1))}")
    print(f"H(M2) = {hex(hash_to_int(MESSAGE_2))}\n")

    ok1 = verify(MESSAGE_1, R, S1)
    ok2 = verify(MESSAGE_2, R, S2)
    print(f"Q3.a signature 1 valid: {ok1}")
    print(f"Q3.a signature 2 valid: {ok2}")


if __name__ == "__main__":
    main()
