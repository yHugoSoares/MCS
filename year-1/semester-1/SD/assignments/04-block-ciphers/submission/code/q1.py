from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

nonce = bytes.fromhex("00000001a5f3c90e7b14d2660048ff21")
ct = bytearray(bytes.fromhex(
    "51073653f3851c51af06c462d293862e93941666f8d561dbefdcc89cd972"
))
key = bytes.fromhex("8b2d1f0a77c4e5519903aab4cde61277")  # verification only

# Flip "00" to "11" at byte positions -6 and -5 (the two leading value digits).
ct[-6] ^= ord("0") ^ ord("1")
ct[-5] ^= ord("0") ^ ord("1")
new_ct = bytes(ct)
print("New ciphertext:", new_ct.hex())

# Verification using the key (not part of the attack).
cipher = Cipher(algorithms.AES(key), modes.CTR(nonce))
decryptor = cipher.decryptor()
print("Decrypted:", (decryptor.update(new_ct) + decryptor.finalize()).decode())
