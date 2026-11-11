# SD — Data Security

MSc in Cybersecurity, University of Minho, 2026/27.
Lecturer: João Marco Silva (DI).

Cryptography from the ground up: security properties and threat models, classical
ciphers, stream ciphers, block ciphers and modes of operation, then a group project.

## Contents

```text
theory/         lecture slides
assignments/    five graded assignments
sd2627/         group project (git submodule)
```

## Assignments

| #  | Folder                 | Topic                                        | Due        |
| -- | ---------------------- | -------------------------------------------- | ---------- |
| 01 | `01-threat-models`     | Security properties, requirements, threat models | 02/10/2026 |
| 02 | `02-classical-ciphers` | Classical cryptographic schemes (monoalphabetic attack) | 09/10/2026 |
| 03 | `03-stream-ciphers`    | Stream ciphers (OTP reuse, crib-dragging)    | 16/10/2026 |
| 04 | `04-block-ciphers`     | Block ciphers and modes of operation         | 23/11/2026 |
| 05 | `05-openssl`           | OpenSSL exercise: ChaCha20 and CMS           | —          |

Each folder contains the statement (`assignment.pdf`), the report source and PDF, and the
code where applicable. Where the submitted bundle differs from the final report, it is kept
in `submission/` (04) or as `submission.zip` (03).

Build a report with:

```sh
cd assignments/01-threat-models
pdflatex report.tex
```

`05-openssl` is driven by its own `Makefile` (`make help`).

## Project

`sd2627` is a **git submodule** for
[marcosevegrand/sd2627](https://github.com/marcosevegrand/sd2627) — a privacy-preserving
incident-sharing platform for network-operator federations (Go, zk-SNARKs).

```sh
git submodule update --init --recursive
cd sd2627 && make help
```

Its own `README.md` and `docs/` cover the architecture and the plan.

## Theory

`theory/` holds the eight lecture decks, mirrored from eLearning:

- `00 DS Presentation`
- `01 DS Introduction and Concepts`
- `02 Symmetric cryptography — Classical techniques`
- `03 Symmetric cryptography — Stream ciphers`
- `04 Symmetric cryptography — Block ciphers`
- `05 Data integrity — Cryptographic hash functions`
- `06 Data integrity — MAC and Authenticated encryption`
- `07 Asymmetric cryptography`

Re-sync with `python3 tools/elearning-sync/sync.py --course SD`.
