#!/usr/bin/env python3
import random
from datetime import datetime, timezone
from pathlib import Path

q1input = bytes.fromhex("fed447773bd63bb2ebe347d620cae2056c40b47205189318412df6ddc1e15d384d4a159210")
q2input = "File-otp-Q2.txt"
c1 = bytes.fromhex("98502a8cdda9ed53b972bde97a7c80f72495d57d044e11aed94d7e4a2e647fa67a8b57eb6ec7b032493f1f58989567106fbf5d1c7016ad6a9b")
c2 = bytes.fromhex("9640268dddaded59ab72baea7a728cf0239ad87b135a16aec5427f5139666ab07d8d4de960d4bd21593f1342968b7c1e60b755126117b87191adc2774476fcb4782b01787a633e78b4ff4134816aa5a43ed8")
c3 = bytes.fromhex("824e2e88c7adff59af72bdf0727380eb3790d07c17421baace4169462e766aa4619845")
c4 = bytes.fromhex("9640268dddaded59ab72baea7a728ffe3f84d06c174517aecb407b46316866af7a8552e06cc1b62750291f529c80681161a55f16770bb06b9db2d5645767f0b17b2b07787363206da1fb4121856caca325d85ad92cc7cb51212b4cc58c")
c5 = bytes.fromhex("944f2e9ecba9fa54bc79a6eb757b8cfc399ac26c004416badf417550356266af7b9a41f769c1b127503f025f9e9f6a176fa55f00761eb66b9ba6d3734571f2bd72231e7c7975316bb4f3")
c6 = bytes.fromhex("98502e9fcebdfc59ae73adf07e679dfe359bdf7017480aafc5416253306a7da2798b56e07ad0b13f5620165598956d1e7db64b066711ba6e95acd1715e73ebb5")
q3input = [c1, c2, c3, c4, c5, c6]
q4input = bytes.fromhex("caffea70ef5b03e9f898bebf13e125a8b81e1a75aea1f20e176bbbc0071a")
q5input = bytes.fromhex("40f46b33dc3c5461a03b6dafa8bdcec8e41163067bd61ac0e3760d3ca4bdb22b08b61d961c")


def xor(a: bytes, b: bytes) -> bytes:
    return bytes(x ^ y for x, y in zip(a, b))

def decrypt(ciphertext: bytes, keystream: bytes) -> str:
    return xor(ciphertext, keystream).decode()

def q1():
    
    start = int(datetime(2026, 9, 15, 10, 0, tzinfo=timezone.utc).timestamp())
    end = int(datetime(2026, 9, 15, 11, 0, tzinfo=timezone.utc).timestamp())
    for seed in range(start, end + 1):
        ks = random.Random(seed).randbytes(len(q1input))
        pt = xor(q1input, ks)
        if all(32 <= b < 127 for b in pt):
            print("Q1 seed:", seed)
            print("Q1 msg:", pt.decode())
            return

def q2():
    cmds = [b"OPEN", b"CLOSE", b"RESET", b"BYPASS", b"SHUTDOWN"]
    cts = [bytes.fromhex(l.split("-")[1].strip()) for l in Path(q2input).read_text().splitlines()]
    keys = sorted({xor(c, p) for c in cts for p in cmds if len(c) == len(p) == 8})
    print("Q2 nkeys:", len(keys))
    for k in keys:
        print("Q2 key:", k.hex())
    for c in sorted(set(cts)):
        for k in keys:
            pt = xor(c, k[:len(c)])
            if pt in cmds:
                print(c.hex(), "->", pt.decode(), "(key " + k.hex()[:8] + "..)")
                break

def q3():
    cts = q3input
    n = len(cts[2])  # 35: so precisamos dos primeiros 35 bytes de cada texto

    # Bytes de keystream que dao letra maiuscula em todos os textos
    options = [[k for k in range(256)
                if all(65 <= (c[pos] ^ k) <= 90 for c in cts)]
               for pos in range(n)]

    def try_word(pos, word):
        ks = [c ^ p for c, p in zip(cts[2][pos:], word.encode())]
        if any(k not in options[pos + j] for j, k in enumerate(ks)):
            return None
        return [bytes(c[pos + j] ^ k for j, k in enumerate(ks)).decode()
                for c in cts]

    trials = [(0, "QUE"), (0, "NAO"), (0, "UMA"),
              (3, "COISA"), (3, "CHAVE"),
              (8, "SECRETA"), (8, "FORTE"), (8, "REUTILIZADA"),
              (19, "NUNCA"), (19, "DEIXA"),
              (24, "DE"), (26, "SER"), (29, "SEGURA")]
    for pos, word in trials:
        frags = try_word(pos, word)
        print(f"Q3 {word}@{pos}:",
              " | ".join(frags) if frags else "REJECT (not A-Z)")

    accepted = [(0, "UMA"), (3, "CHAVE"), (8, "REUTILIZADA"),
                (19, "DEIXA"), (24, "DE"), (26, "SER"), (29, "SEGURA")]
    keystream = [None] * n
    for pos, word in accepted:
        assert try_word(pos, word) is not None
        for j, p in enumerate(word.encode()):
            keystream[pos + j] = cts[2][pos + j] ^ p
    assert None not in keystream

    ks = bytes(keystream)
    print("Q3 key:", ks.hex())
    for i, c in enumerate(cts, 1):
        print(f"Q3 T{i}:", bytes(a ^ b for a, b in zip(c, ks)).decode())

def q4():
    p = b"PLC=07;CMD=SET;NAOH_PPM=00100;"
    pp = b"PLC=07;CMD=SET;NAOH_PPM=11100;"
    print("Q4 forged:", xor(q4input, xor(p, pp)).hex())

def q5():
    p1 = b"HEARTBEAT;PLC=07;STATUS=OK;NAOH_PPM=00100;PH=07.4;"
    c1 = bytes.fromhex("58fd695cb8492a63b94400b0aed4aea89b7967106bbe1d8f9f5c4253b59ece1a2cc5629d17967fca02e28638fb6ffc083e1d")
    print("Q5 msg:", xor(q5input, xor(c1, p1)[:len(q5input)]).decode())

if __name__ == "__main__":
    print("=== Q1 ===")
    q1()
    print("\n=== Q2 ===")
    q2()
    print("\n=== Q3 ===")
    q3()
    print("\n=== Q4 ===")
    q4()
    print("\n=== Q5 ===")
    q5()
