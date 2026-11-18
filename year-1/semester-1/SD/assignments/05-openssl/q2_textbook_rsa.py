#!/usr/bin/env python3
"""Q2 - Textbook RSA signatures and the multiplicative forgery.

Q2.a signs and verifies without hashing or padding: s = m^d mod n.
Q2.b shows that, given valid signatures s1 and s2 on m1 and m2, anyone can
compute a valid signature on m3 = m1 * m2 mod n: s3 = s1 * s2 mod n.

Usage: python3 q2_textbook_rsa.py
"""

from __future__ import annotations

from cryptography.hazmat.primitives.asymmetric import rsa

M1 = b"TRANSFER 500 EUR TO ACCOUNT PT50-0001"
M2 = b"TRANSFER 20 EUR TO ACCOUNT PT50-0002"


def bytes_to_int(data: bytes) -> int:
    return int.from_bytes(data, "big")


def int_to_bytes(value: int) -> bytes:
    return value.to_bytes((value.bit_length() + 7) // 8, "big")


def textbook_sign(m: int, d: int, n: int) -> int:
    return pow(m, d, n)


def textbook_verify(m: int, s: int, e: int, n: int) -> bool:
    return pow(s, e, n) == m


def main() -> None:
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    numbers = key.private_numbers()
    public = numbers.public_numbers
    n, e, d = public.n, public.e, numbers.d
    print(f"RSA modulus: {n.bit_length()} bits")
    print(f"e = {e}, d < n: {d < n}\n")

    # --- Q2.a: honest textbook signing/verification --------------------------
    m1, m2 = bytes_to_int(M1), bytes_to_int(M2)
    assert m1 < n and m2 < n

    s1 = textbook_sign(m1, d, n)
    s2 = textbook_sign(m2, d, n)
    print("Q2.a")
    print(f"  m1 = int({M1.decode()!r}) ({m1.bit_length()} bits)")
    print(f"  s1 = {hex(s1)[:34]}...")
    print(f"  verify(m1, s1) = {textbook_verify(m1, s1, e, n)}")
    print(f"  verify(m2, s2) = {textbook_verify(m2, s2, e, n)}")
    print(f"  tampered message verifies? "
          f"{textbook_verify(m1 + 1, s1, e, n)}\n")

    # --- Q2.b: forge signature on m3 = m1 * m2 -------------------------------
    m3 = (m1 * m2) % n
    s3 = (s1 * s2) % n
    forged_ok = textbook_verify(m3, s3, e, n)
    print("Q2.b")
    print(f"  m3 = m1 * m2 mod n ({m3.bit_length()} bits)")
    print(f"  m3 as bytes: {int_to_bytes(m3)[:24]!r}... (not meaningful text)")
    print(f"  s3 = s1 * s2 mod n = {hex(s3)[:34]}...")
    print(f"  verify(m3, s3) with the public key = {forged_ok}")
    print(f"  signature was produced without d: {forged_ok}")
    print()
    print("  The forgery is existential: it yields a NEW message (the product)")
    print("  for existing signatures, not a chosen/fraudulent signature on a")
    print("  message the attacker picked in advance.")


if __name__ == "__main__":
    main()
