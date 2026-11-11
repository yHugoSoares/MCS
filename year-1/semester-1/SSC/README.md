# SSC — Computer Systems Security

MSc in Cybersecurity, University of Minho, 2026/27.

Linux systems security: authentication stacks (PAM), federated identity (OIDC), SSH
certificates and hardening, privilege escalation (setuid/sudo, capabilities) and MAC
(AppArmor).

## Contents

```text
theory/     lecture slides
guides/     the course guide set: 00-05 + labs 06-08
labs/       per-lab notes and logs
reports/    the three written deliverables (LaTeX sources + PDF)
Makefile    builds the reports
```

## Guides

| File | Topic |
| ---- | ----- |
| `00 - Getting Ready.pdf` | Lab setup |
| `01 - Environment Setup and First Contact.pdf` | First contact with the VM |
| `02 - Threat Modelling.pdf` | Threat modelling |
| `03 - PAM and the Authentication Stack.pdf` | PAM |
| `04 - OIDC and Federated Identity.pdf` | OIDC |
| `05 - ssh certificates and hardening.pdf` | SSH certificates |
| `lab-06-setuid-and-sudo.pdf` | setuid and sudo |
| `lab-07-linux-capabilities.pdf` | Linux capabilities |
| `lab-08-apparmor-and-intrusion-detection.pdf` | AppArmor and detection |

## Labs

Working notes and captured output for each lab (`lab3-log.txt`, `lab4-notes.md`,
`lab5.md` … `lab8.md`, plus `lab8-final-profile`). These feed the reports.

## Reports

| Report | Block | Covers |
| ------ | ----- | ------ |
| `report1` | 1 | Labs 1–2: first contact, threat modelling |
| `report2` | 2 | Labs 3–5: PAM, OIDC, SSH certificates |
| `report3` | 3 | Labs 6–8: setuid/sudo, capabilities, AppArmor |

```sh
make            # help
make all        # build every report and clean aux files
make report2    # build a single report
make distclean  # remove aux files and PDFs
```

Figures live in `reports/images/` and are referenced with `\graphicspath{{images/}}`, so
the build must run from `reports/` (the `Makefile` already does that).

## Theory

`theory/` holds the eight lecture decks plus the Week 0 introduction, flat:

- `week-0-getting-ready`
- `lecture-01-foundations-of-systems-security`
- `lecture-02-threat-modelling-in-practice`
- `lecture-03-authentication-nss-and-pam`
- `lecture-04-federated-identity`
- `lecture-05-authorisation-and-ssh`
- `lecture-06-privilege-setuid-and-sudo`
- `lecture-07-linux-capabilities`
- `lecture-08-mandatory-access-control-and-detection`

The lab guides live in [`guides/`](#guides); the sync script skips them because they are
already there. Re-sync with `python3 tools/elearning-sync/sync.py --course SSC`.
