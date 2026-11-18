#!/usr/bin/env python3
"""Q1.a - HMAC-SHA256 versus RSA-PSS signatures.

For the same message, compute and verify an HMAC tag with a shared key K and
an RSA-PSS signature with a 2048-bit key pair.  Print key/tag/signature sizes
and per-operation timings (mean over many executions).

Usage: python3 q1a_hmac_vs_rsa.py [--iterations N]
"""

from __future__ import annotations

import argparse
import os
import statistics
import time

from cryptography.hazmat.primitives import hashes, hmac, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa

MESSAGE = b"TRANSFER 500 EUR TO ACCOUNT PT50-0001"


def timed(fn, iterations: int) -> tuple[float, float, float]:
    """Run fn iterations times and return (mean, median, ops/s) in microseconds."""
    for _ in range(min(16, iterations)):  # warm-up
        fn()
    samples = []
    start = time.perf_counter_ns()
    for _ in range(iterations):
        t0 = time.perf_counter_ns()
        fn()
        samples.append(time.perf_counter_ns() - t0)
    elapsed = time.perf_counter_ns() - start
    mean_us = statistics.fmean(samples) / 1_000
    median_us = statistics.median(samples) / 1_000
    ops_s = iterations / (elapsed / 1_000_000_000)
    return mean_us, median_us, ops_s


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--iterations", type=int, default=1000)
    parser.add_argument("--rsa-iterations", type=int, default=500)
    args = parser.parse_args()

    # --- HMAC-SHA256 with a shared 256-bit key -------------------------------
    hmac_key = os.urandom(32)

    def hmac_tag() -> bytes:
        h = hmac.HMAC(hmac_key, hashes.SHA256())
        h.update(MESSAGE)
        return h.finalize()

    tag = hmac_tag()

    def hmac_verify() -> None:
        h = hmac.HMAC(hmac_key, hashes.SHA256())
        h.update(MESSAGE)
        h.verify(tag)

    hmac_verify()  # sanity check: must not raise
    hmac_sign_us, hmac_sign_med, hmac_sign_ops = timed(hmac_tag, args.iterations)
    hmac_ver_us, hmac_ver_med, hmac_ver_ops = timed(hmac_verify, args.iterations)

    # --- RSA-PSS (2048-bit, SHA-256, 32-byte salt) ---------------------------
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    public_key = private_key.public_key()
    pss = padding.PSS(mgf=padding.MGF1(hashes.SHA256()), salt_length=32)

    def rsa_sign() -> bytes:
        return private_key.sign(MESSAGE, pss, hashes.SHA256())

    signature = rsa_sign()

    def rsa_verify() -> None:
        public_key.verify(signature, MESSAGE, pss, hashes.SHA256())

    rsa_verify()  # sanity check: must not raise
    rsa_sign_us, rsa_sign_med, rsa_sign_ops = timed(rsa_sign, args.rsa_iterations)
    rsa_ver_us, rsa_ver_med, rsa_ver_ops = timed(rsa_verify, args.rsa_iterations)

    priv_der = private_key.private_bytes(
        serialization.Encoding.DER,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    )
    pub_der = public_key.public_bytes(
        serialization.Encoding.DER,
        serialization.PublicFormat.SubjectPublicKeyInfo,
    )

    print(f"Message: {MESSAGE.decode()} ({len(MESSAGE)} bytes)\n")

    print("HMAC-SHA256 (shared key)")
    print(f"  shared key:          {len(hmac_key)} bytes")
    print(f"  tag:                 {len(tag)} bytes")
    print(f"  tag generation:      {hmac_sign_us:8.3f} us  (median {hmac_sign_med:.3f}, {hmac_sign_ops:,.0f} ops/s)")
    print(f"  tag verification:    {hmac_ver_us:8.3f} us  (median {hmac_ver_med:.3f}, {hmac_ver_ops:,.0f} ops/s)")
    print(f"  iterations:          {args.iterations}\n")

    print("RSA-PSS-2048 / SHA-256 (public-key pair)")
    print(f"  private key (DER):   {len(priv_der)} bytes")
    print(f"  public key (DER):    {len(pub_der)} bytes")
    print(f"  signature:           {len(signature)} bytes")
    print(f"  signing:             {rsa_sign_us:8.3f} us  (median {rsa_sign_med:.3f}, {rsa_sign_ops:,.0f} ops/s)")
    print(f"  verification:        {rsa_ver_us:8.3f} us  (median {rsa_ver_med:.3f}, {rsa_ver_ops:,.0f} ops/s)")
    print(f"  iterations:          {args.rsa_iterations}\n")

    print("Ratios (RSA / HMAC)")
    print(f"  signature size:      {len(signature) / len(tag):.1f}x")
    print(f"  signing cost:        {rsa_sign_us / hmac_sign_us:.1f}x")
    print(f"  verification cost:   {rsa_ver_us / hmac_ver_us:.1f}x")
    print(f"  trusted key material: {len(pub_der)} B public vs {len(hmac_key)} B shared secret")


if __name__ == "__main__":
    main()
