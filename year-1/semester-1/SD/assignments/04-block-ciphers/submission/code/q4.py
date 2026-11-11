from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

nonce = bytes.fromhex("a0acc5b086bb58000c5b0d31")
ct = bytearray(bytes.fromhex(
    "8fc0cc2e6567e77bcfaad7c8363ae39b2db91d4df9aa5acb75dce650cfe6"
))
tag = bytes.fromhex("a903a1a5b290dfe9d41c2634deed9cb1")
key = bytes.fromhex("3a1c9f44db2e7780015566aabbcc9911")

# Flip "00" to "11" at byte positions -6 and -5.
ct[-6] ^= ord("0") ^ ord("1")
ct[-5] ^= ord("0") ^ ord("1")

# AES-GCM expects the tag appended to the ciphertext.
forged_data = bytes(ct) + tag

try:
    pt = AESGCM(key).decrypt(nonce, forged_data, None)
    print("Decrypted:", pt.decode())
except InvalidTag:
    print("Decryption failed: InvalidTag raised, forged message rejected.")
