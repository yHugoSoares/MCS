cts = {
    "C1": "b3f54ffd243d5764117c2751a130813068e1caf62ab7e794b90583176eeb9fc6"
          "542b191dd3114c5cdf9f06c11bbc31e0a2914503499340c978b69b612fcd6a6a",
    "C2": "a22cbbd3231e96c2e1300049d5ca045abbd343ee4ac57cbb1110f709dfeddd19"
          "143bf488dccb3bcf42644f665d08c99f57d3dfc3b1d11f4f952474ae36f72917",
    "C3": "b3f54ffd243d5764117c2751a130813068e1caf62ab7e794b90583176eeb9fc6"
          "542b191dd3114c5cdf9f06c11bbc31e0a2914503499340c978b69b612fcd6a6a",
    "C4": "456437c5194fde6cbcd694083dec9478d26e0d34661e257da479f73c4952885c"
          "577dd28d11e6d4c26e7de22affd8b8dbbb3b4fd998882afc390432cfb1e99781",
}

# Compare every pair of full ciphertexts.
names = list(cts)
for i, name in enumerate(names):
    for other in names[i + 1:]:
        result = "identical" if cts[name] == cts[other] else "different"
        print(f"{name} and {other}: {result}")

# Split into 16-byte (32 hex chars) blocks to see block-level leaks.
for name, ct in cts.items():
    blocks = [ct[i:i + 32] for i in range(0, len(ct), 32)]
    print(f"{name} blocks: {blocks}")
