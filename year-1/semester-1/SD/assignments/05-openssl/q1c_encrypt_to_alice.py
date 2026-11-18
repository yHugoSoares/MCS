#!/usr/bin/env python3
"""Q1.c - Encryption with Alice's public key does not authenticate the sender.

Bob is *not* involved.  Mallory generates her own message, encrypts it with
Alice's public key and sends the ciphertext.  Alice decrypts it successfully
and has no way to tell that it did not come from Bob.

Usage: python3 q1c_encrypt_to_alice.py
"""

from __future__ import annotations

import base64

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa

OAEP = padding.OAEP(
    mgf=padding.MGF1(algorithm=hashes.SHA256()),
    algorithm=hashes.SHA256(),
    label=None,
)
PSS = padding.PSS(mgf=padding.MGF1(hashes.SHA256()), salt_length=32)


def main() -> None:
    # Alice's key pair.  Only the public half is published.
    alice_private = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    alice_public = alice_private.public_key()
    alice_pub_pem = alice_public.public_bytes(
        serialization.Encoding.PEM,
        serialization.PublicFormat.SubjectPublicKeyInfo,
    )

    # Bob's key pair exists, but Mallory does not have it.
    bob_private = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    bob_public = bob_private.public_key()

    print("Alice publishes:")
    print(alice_pub_pem.decode())

    # --- Mallory forges a message "from Bob" ---------------------------------
    forged = b"TRANSFER 99999 EUR TO ACCOUNT PT50-6666 -- Bob"
    ciphertext = alice_public.encrypt(forged, OAEP)  # anyone can do this
    print("Mallory sends ciphertext (base64):")
    print(base64.b64encode(ciphertext).decode())
    print(f"ciphertext length: {len(ciphertext)} bytes\n")

    # --- What Alice sees -----------------------------------------------------
    plaintext = alice_private.decrypt(ciphertext, OAEP)
    print("Alice decrypts successfully:")
    print(f"  {plaintext.decode()}")
    print("Alice cannot tell who created the ciphertext: it only proves that")
    print("the sender knew her public key, which is public.\n")

    # --- A signature would be the missing proof ------------------------------
    # Mallory can sign with her own key, but not with Bob's.
    mallory_private = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    mallory_signature = mallory_private.sign(forged, PSS, hashes.SHA256())
    try:
        bob_public.verify(mallory_signature, forged, PSS, hashes.SHA256())
    except InvalidSignature:
        print("Mallory's signature does NOT verify with Bob's public key.")

    # Bob can, because only he has his private key.
    bob_signature = bob_private.sign(forged, PSS, hashes.SHA256())
    bob_public.verify(bob_signature, forged, PSS, hashes.SHA256())
    print("Bob's signature verifies with Bob's public key: the source is proven.")


if __name__ == "__main__":
    main()
