#!/usr/bin/env python3
"""Q3.b/Q3.c - DSA nonce reuse: recover k, recover x, forge a signature.

Both signatures share r, so the same per-message nonce k was reused:

    s1 = k^-1 (H1 + x r) mod q
    s2 = k^-1 (H2 + x r) mod q

Subtracting and solving:

    k = (H1 - H2) * (s1 - s2)^-1 mod q
    x = (s1 * k - H1) * r^-1     mod q

The recovered x must satisfy y = g^x mod p.  It is then used to sign any
message, here "TRANSFER 99999 EUR TO ACCOUNT PT50-6666", and q3a_dsa_verify.py
checks the forged signature.

Usage: python3 q3c_dsa_attack.py
"""

from __future__ import annotations

from q3a_dsa_verify import (
    G,
    MESSAGE_1,
    MESSAGE_2,
    P,
    Q,
    R,
    S1,
    S2,
    Y,
    hash_to_int,
    verify,
)

TARGET = "TRANSFER 99999 EUR TO ACCOUNT PT50-6666"
K3 = 0x5EED_1234_ABCD_0001  # attacker-chosen nonce for the forged signature


def main() -> None:
    h1 = hash_to_int(MESSAGE_1)
    h2 = hash_to_int(MESSAGE_2)

    # --- Recover the reused nonce k -----------------------------------------
    k = (h1 - h2) * pow(S1 - S2, -1, Q) % Q
    print("Q3.b")
    print(f"  k  = {hex(k)}")

    # --- Recover the private key x ------------------------------------------
    x = (S1 * k - h1) * pow(R, -1, Q) % Q
    print(f"  x  = {hex(x)}")
    print(f"  y == g^x mod p: {pow(G, x, P) == Y}\n")

    # --- Forge a signature on a new message ---------------------------------
    h3 = hash_to_int(TARGET)
    r3 = pow(G, K3, P) % Q
    s3 = pow(K3, -1, Q) * (h3 + x * r3) % Q
    print("Q3.c")
    print(f"  message = {TARGET!r}")
    print(f"  k3 = {hex(K3)}")
    print(f"  r3 = {hex(r3)}")
    print(f"  s3 = {hex(s3)}")
    print(f"  forged signature verifies: {verify(TARGET, r3, s3)}")

    # A signature from the same key on an unrelated message must still verify,
    # which shows the key really was recovered.
    print(f"  control (original message 1): {verify(MESSAGE_1, R, S1)}")


if __name__ == "__main__":
    main()
