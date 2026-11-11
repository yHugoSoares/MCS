from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

iv0 = bytes.fromhex("00000000000000000000000000001000")
c0  = bytes.fromhex("8e00a77c9519e662e83144b473edb147")
iv1 = bytes.fromhex("00000000000000000000000000001001")
key = bytes.fromhex("c0ffee1122334455aabbccddeeff0011")  # oracle emulation only
oracle_counter = int.from_bytes(iv1, "big")

def encryption_oracle(chosen_plaintext):
    global oracle_counter
    iv = oracle_counter.to_bytes(16, "big")
    oracle_counter += 1
    encryptor = Cipher(algorithms.AES(key), modes.CBC(iv)).encryptor()
    return encryptor.update(chosen_plaintext) + encryptor.finalize()

# Predict each query's IV without using the key.
next_counter = int.from_bytes(iv1, "big")
for i in range(100):
    next_iv = next_counter.to_bytes(16, "big")
    guess = f"PLC={i:02d};CMD=SET;N".encode("ascii")
    injected_block = bytes(g ^ a ^ b for g, a, b in zip(guess, iv0, next_iv))
    response = encryption_oracle(injected_block)
    next_counter += 1
    if response[:16] == c0:
        print(f"Recovered <id>: {i:02d}")
        print(f"Full first block: {guess.decode()}")
        break
else:
    raise RuntimeError("No matching id found")
