#!/usr/bin/env python3
from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM


def xor(a: bytes, b: bytes) -> bytes:
    return bytes(x ^ y for x, y in zip(a, b))

def ctr_crypt(key: bytes, nonce: bytes, data: bytes) -> bytes:
    c = Cipher(algorithms.AES(key), modes.CTR(nonce)).encryptor()
    return c.update(data) + c.finalize()

def cbc_encrypt(key: bytes, iv: bytes, data: bytes) -> bytes:
    c = Cipher(algorithms.AES(key), modes.CBC(iv)).encryptor()
    return c.update(data) + c.finalize()

def ecb_encrypt(key: bytes, data: bytes) -> bytes:
    c = Cipher(algorithms.AES(key), modes.ECB()).encryptor()
    return c.update(data) + c.finalize()


# Q1
q1_nonce = bytes.fromhex("00000001a5f3c90e7b14d2660048ff21")
q1_ct = bytes.fromhex("51073653f3851c51af06c462d293862e93941666f8d561dbefdcc89cd972")
q1_key = bytes.fromhex("8b2d1f0a77c4e5519903aab4cde61277")

# Q2
q2_cts = [
    bytes.fromhex("b3f54ffd243d5764117c2751a130813068e1caf62ab7e794b90583176eeb9fc6"
                  "542b191dd3114c5cdf9f06c11bbc31e0a2914503499340c978b69b612fcd6a6a"),
    bytes.fromhex("a22cbbd3231e96c2e1300049d5ca045abbd343ee4ac57cbb1110f709dfeddd19"
                  "143bf488dccb3bcf42644f665d08c99f57d3dfc3b1d11f4f952474ae36f72917"),
    bytes.fromhex("b3f54ffd243d5764117c2751a130813068e1caf62ab7e794b90583176eeb9fc6"
                  "542b191dd3114c5cdf9f06c11bbc31e0a2914503499340c978b69b612fcd6a6a"),
    bytes.fromhex("456437c5194fde6cbcd694083dec9478d26e0d34661e257da479f73c4952885c"
                  "577dd28d11e6d4c26e7de22affd8b8dbbb3b4fd998882afc390432cfb1e99781"),
]

# Q3
q3_iv0 = bytes.fromhex("00000000000000000000000000001000")
q3_c0 = bytes.fromhex("8e00a77c9519e662e83144b473edb147")
q3_iv1 = bytes.fromhex("00000000000000000000000000001001")
q3_key = bytes.fromhex("c0ffee1122334455aabbccddeeff0011")

# Q4
q4_nonce = bytes.fromhex("a0acc5b086bb58000c5b0d31")
q4_ct = bytes.fromhex("8fc0cc2e6567e77bcfaad7c8363ae39b2db91d4df9aa5acb75dce650cfe6")
q4_tag = bytes.fromhex("a903a1a5b290dfe9d41c2634deed9cb1")
q4_key = bytes.fromhex("3a1c9f44db2e7780015566aabbcc9911")


def q1():
    p = b"PLC=07;CMD=SET;NAOH_PPM=00100;"
    pp = b"PLC=07;CMD=SET;NAOH_PPM=11100;"
    print("Q1 plaintext check:", ctr_crypt(q1_key, q1_nonce, q1_ct).decode())
    forged = xor(q1_ct, xor(p, pp))
    print("Q1 forged:", forged.hex())
    print("Q1 decrypts to:", ctr_crypt(q1_key, q1_nonce, forged).decode())
    print("Q1 changed bytes:",
          [(i, hex(a), hex(b)) for i, (a, b) in enumerate(zip(q1_ct, forged)) if a != b])


def q2():
    def split_blocks(c):
        return [c[k:k + 16] for k in range(0, len(c), 16)]

    blocks = [split_blocks(c) for c in q2_cts]
    for i, c in enumerate(q2_cts, 1):
        print(f"Q2 C{i} len={len(c)} blocks={len(c) // 16}")
    for i in range(len(q2_cts)):
        for j in range(i + 1, len(q2_cts)):
            same = q2_cts[i] == q2_cts[j]
            eq = sum(a == b for a, b in zip(blocks[i], blocks[j]))
            print(f"Q2 C{i + 1} vs C{j + 1}: identical={same}, equal blocks={eq}")

    # demonstracao: mesma chave ECB, comandos so diferentes no valor
    def pad(d):
        n = 16 - len(d) % 16
        return d + bytes([n]) * n

    demo_key = bytes(range(16))
    p1 = pad(b"PLC=07;CMD=SET;NAOH_PPM=00100;")
    p2 = pad(b"PLC=07;CMD=SET;NAOH_PPM=99999;")
    c1, c2 = ecb_encrypt(demo_key, p1), ecb_encrypt(demo_key, p2)
    print("Q2 demo blocks C1:", [b.hex() for b in split_blocks(c1)])
    print("Q2 demo blocks C2:", [b.hex() for b in split_blocks(c2)])
    print("Q2 demo same first block:", c1[:16] == c2[:16])


def q3_oracle(message: bytes, iv: bytes) -> bytes:
    return cbc_encrypt(q3_key, iv, message)


def q3():
    def test_block(guess: bytes, iv: bytes) -> bool:
        # queremos P xor iv == P_guess xor iv0, logo P = P_guess xor iv0 xor iv
        block = b"PLC=" + guess + b";CMD=SET;N"
        assert len(block) == 16
        query = xor(block, xor(q3_iv0, iv))
        return q3_oracle(query, iv)[:16] == q3_c0

    # cada query gasta um IV novo; o contador e previsivel, logo sabemos o IV antes de enviar
    counter = int.from_bytes(q3_iv1, "big")
    matches = []
    for i in range(100):
        iv = counter.to_bytes(16, "big")
        if test_block(f"{i:02d}".encode(), iv):
            matches.append(i)
        counter += 1

    print("Q3 candidate ids:", [f"{m:02d}" for m in matches])
    assert len(matches) == 1
    print("Q3 id:", f"{matches[0]:02d}")

    # verificacao (com a chave, fora da logica do ataque)
    dec = Cipher(algorithms.AES(q3_key), modes.CBC(q3_iv0)).decryptor()
    print("Q3 block:", (dec.update(q3_c0) + dec.finalize()).decode())


def q4():
    p = b"PLC=07;CMD=SET;NAOH_PPM=00100;"
    pp = b"PLC=07;CMD=SET;NAOH_PPM=11100;"
    forged = xor(q4_ct, xor(p, pp))
    try:
        AESGCM(q4_key).decrypt(q4_nonce, forged + q4_tag, None)
        print("Q4 forged accepted (unexpected)")
    except InvalidTag:
        print("Q4 forged rejected: InvalidTag")

    # Q4.b: mesma (key, nonce) em duas mensagens -> mesmo keystream
    secret = b"PLC=07;CMD=SET;NAOH_PPM=99999;"
    ct2 = AESGCM(q4_key).encrypt(q4_nonce, secret, None)[:len(q4_ct)]
    recovered = xor(xor(ct2, q4_ct), p)  # C1^C2^P1 = P2, P1 e publico
    print("Q4.b recovered other:", recovered.decode())


if __name__ == "__main__":
    print("=== Q1 ===")
    q1()
    print("\n=== Q2 ===")
    q2()
    print("\n=== Q3 ===")
    q3()
    print("\n=== Q4 ===")
    q4()
