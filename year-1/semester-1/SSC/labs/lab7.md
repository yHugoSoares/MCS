# Lab 7 — Linux capabilities e least privilege

Results log. Um bloco por exercício: o que se correu, o que se observou, o que prova, o
que vai para o Lab report 3.

Status: **Ex. 1–6 feitos**; P1, P2 e Reflexão escritos no `report3.tex`. Máquina a
repor com o snapshot `lab7-clean` no UTM.

---

## Setup (pre-lab)

- VM `ssc-lab` (Ubuntu 24.04.5 LTS, aarch64, kernel 6.8.0-139), user `student`, via
  `ssh ssc` (`student@127.0.0.1:2222`). Snapshot `lab7-clean` gerido no UTM (fora do
  guest).
- `capsh`/`getcap`/`setcap` presentes em `/usr/sbin`, `gcc` em `/usr/bin`.
- Docker 29.1.3 (pacote `docker.io`), rootful, storage overlayfs.
- **Relógio do guest atrasado**: o RTC dizia 4 Nov mas o sistema dizia 28 Out, e o
  `docker pull` falhava com `x509: certificate has expired or is not yet valid`.
  Corrigido com `sudo date -u -s "2026-11-04 11:24:40"`; imagens `alpine` e
  `python:3.12-alpine` puxadas a seguir.
- `lab7-files.zip` chegou depois (ficheiro `lab7.zip`), copiado para a VM e extraído
  para `~/ssc-lab7` (o zip trazia um directório `lab7/` dentro, achatado). Todos os
  comandos correm a partir de `~/ssc-lab7`.
- Kernel expõe 41 capabilities (`/proc/sys/kernel/cap_last_cap` = 40, logo bits 0..40).

---

## P1 / P2 (avaliadas)

Pendente (responder com os dados do Ex. 1 e 2).

---

## Ex. 1 — os cinco conjuntos (Parte A)

```
$ grep Cap /proc/self/status
CapInh:	0000000000000000
CapPrm:	0000000000000000
CapEff:	0000000000000000
CapBnd:	000001ffffffffff
CapAmb:	0000000000000000

$ capsh --decode=$(grep CapEff /proc/self/status | awk '{print $2}')
0x0000000000000000=

$ capsh --decode=$(grep CapBnd /proc/self/status | awk '{print $2}')
0x000001ffffffffff=cap_chown,cap_dac_override,cap_dac_read_search,cap_fowner,
cap_fsetid,cap_kill,cap_setgid,cap_setuid,cap_setpcap,cap_linux_immutable,
cap_net_bind_service,cap_net_broadcast,cap_net_admin,cap_net_raw,cap_ipc_lock,
cap_ipc_owner,cap_sys_module,cap_sys_rawio,cap_sys_chroot,cap_sys_ptrace,
cap_sys_pacct,cap_sys_admin,cap_sys_boot,cap_sys_nice,cap_sys_resource,cap_sys_time,
cap_sys_tty_config,cap_mknod,cap_lease,cap_audit_write,cap_audit_control,cap_setfcap,
cap_mac_override,cap_mac_admin,cap_syslog,cap_wake_alarm,cap_block_suspend,
cap_audit_read,cap_perfmon,cap_bpf,cap_checkpoint_restore
```

Daemon root (cron):

```
$ pid=$(pgrep -n cron || pgrep -n systemd)
$ sudo grep Cap /proc/$pid/status
CapInh:	0000000000000000
CapPrm:	000001ffffffffff
CapEff:	000001ffffffffff
CapBnd:	000001ffffffffff
CapAmb:	0000000000000000

$ sudo grep -E '^(Uid|Gid):' /proc/$pid/status
Uid:	0	0	0	0
Gid:	0	0	0	0

$ ps -o pid,ruser,euser,comm -p $pid
    PID RUSER    EUSER    COMMAND
    653 root     root     cron
```

Os dois `CapEff`: a minha shell `0x0`, o `cron` `0x1ffffffffff` — o mesmo valor que o
`CapBnd` da shell, ou seja, o conjunto completo deste kernel (41 bits).

### 1a

CapEff da shell é 0; o do cron é 0x1ffffffffff (todas as 41). O `CapBnd` é igual nos
dois (0x1ffffffffff): o tecto não é o que limita a shell, é a ausência de capabilities no
permitted/effective.

Os cinco conjuntos:

- **Permitted (CapPrm)** — o reservatório: capabilities que o processo pode, se quiser,
  activar. Não autoriza nada por si.
- **Effective (CapEff)** — as que estão activas; é este conjunto que o kernel consulta a
  cada operação privilegiada.
- **Inheritable (CapInh)** — as que podem ser herdadas por um programa executado sem
  privilégio (com `execve`, entra no cálculo do permitted do novo processo).
- **Bounding (CapBnd)** — o tecto: máscara aplicada pelo kernel no `execve`, que impede
  ganhar capabilities fora dela. Não tira as que o processo já tem.
- **Ambient (CapAmb)** — as que sobrevivem ao `execve` de um binário não privilegiado e
  ficam logo no permitted **e** effective do novo programa.

O effective, e não o permitted, decide o syscall porque o kernel testa
`cap_capable()` contra o effective: ter uma capability no permitted só significa poder
promovê-la com `capset()`. É essa separação que permite a um processo baixar o
effective durante uma operação arriscada e voltar a levantá-lo depois, sem perder o
direito — o permitted é o que se conserva, o effective é o que se usa agora.

A shell não precisa de nada porque corre como `student` (uid 1000); o `cron` é um daemon
de root lançado pelo systemd, logo herda o conjunto completo.

---

## Ex. 2 — setuid vs file capability (Parte B)

Corrido em `~/ssc-lab7`. `ip_unprivileged_port_start` na VM = 1024, logo :80 é
privilegiada.

```
$ gcc -o ~/capbind lab7-bind80.c
$ ~/capbind
FAIL: bind :80 denied: Permission denied (uid=1000 euid=1000)
rc=1

$ sudo cp ~/capbind ~/capbind_suid
$ sudo chown root ~/capbind_suid
$ sudo chmod u+s ~/capbind_suid
$ ls -l ~/capbind_suid
-rwsr-xr-x 1 root root 71008 Nov  4 11:34 /home/student/capbind_suid
$ ~/capbind_suid
BOUND :80 OK (uid=1000 euid=0)
rc=0

$ sudo cp ~/capbind ~/capbind_cap
$ sudo setcap cap_net_bind_service+ep ~/capbind_cap
$ getcap ~/capbind_cap
/home/student/capbind_cap cap_net_bind_service=ep
$ ls -l ~/capbind_cap
-rwxr-xr-x 1 root root 71008 Nov  4 11:34 /home/student/capbind_cap
$ ~/capbind_cap
BOUND :80 OK (uid=1000 euid=1000)
rc=0
```

Três execuções do mesmo programa: sem privilégio falha; com setuid liga `euid=0` e
liga; com a file capability liga com `euid=1000` e uid 1000.

### 2a

As duas versões ligam :80, mas o que corre é diferente. Na versão setuid o `execve`
põe o **effective UID a 0** (e o saved set-user-ID a 1000): o programa é, durante
toda a execução, um processo de root. Pode tudo o que root pode — `CAP_DAC_OVERRIDE`
e `CAP_DAC_READ_SEARCH` (ler/escrever qualquer ficheiro), `CAP_CHOWN`,
`CAP_SETUID`/`CAP_SETGID`, `CAP_KILL`, `CAP_SYS_PTRACE`, `CAP_SYS_MODULE`,
`CAP_SYS_ADMIN`, `CAP_NET_ADMIN`/`CAP_NET_RAW`, etc. — e a única coisa que o impede de
o fazer é não haver código para isso no binário. Qualquer bug de memória, qualquer
argumento ou variável de ambiente mal tratada, passa a ser execução como root; e quem
puder escrever no ficheiro passa a ter root directo.

Na versão com file capability o euid continua 1000 e o real UID também; o que o
`execve` acrescenta é **uma** capability, `CAP_NET_BIND_SERVICE`, no permitted e no
effective do processo (por causa de `+ep`). Tudo o resto fica a zero. Negou a si
próprio o resto do root: não pode fazer override de permissões, não pode mudar donos,
não pode matar processos de outros utilizadores, não pode ptrace, não pode carregar
módulos nem mexer na rede. É o argumento de least privilege concreto: o binário
declara antecipadamente a única coisa de que precisa, e o kernel dá-lhe só isso.

### 2b

```
$ sudo setcap -r ~/capbind_cap
$ getcap ~/capbind_cap          # (sem saída)
$ ~/capbind_cap
FAIL: bind :80 denied: Permission denied (uid=1000 euid=1000)
rc=1
```

Usei `setcap -r`, que o setcap(8) descreve como «The special capability string, '-r',
is used to remove a capability set from a file». É o clean-up correcto porque repõe o
ficheiro no estado sem privilégio nenhum e é verificável com `getcap` (que passa a não
imprimir nada) — ao contrário de `setcap cap_net_bind_service-ep`, que subtrai só uma
capability e deixa o resto do conjunto por tocar. Também não confundir com «conjunto
vazio»: o manual nota que um conjunto vazio não é o mesmo que remover o conjunto.

`ping`:

```
$ ls -l /usr/bin/ping
-rwxr-xr-x 1 root root 146992 Jul 24  2025 /usr/bin/ping
$ getcap /usr/bin/ping
/usr/bin/ping cap_net_raw=ep
```

O `ping` desta imagem não é setuid: tem `cap_net_raw=ep`. Um socket raw é uma
operação privilegiada, mas só precisa de `CAP_NET_RAW`; em vez de dar ao processo o
root inteiro (setuid), o pacote `iputils-ping` dá-lhe essa única capability. Assim o
`ping` corre com o uid de quem o chama e não ganha mais nada — e, ao contrário do
setuid, não há um binário que, se tiver um bug, corre como root.

Limpeza: `rm -f ~/capbind_suid` (a cópia setuid não deve ficar na máquina, como o
enunciado pede). `~/capbind_cap` fica, já sem capability.

---

## Ex. 3 — default vs privileged, e depois --user 1000 (Parte C)

### 3a — o default e o --privileged

```
$ docker run --rm alpine sh -c "grep Cap /proc/self/status"
CapInh:	0000000000000000
CapPrm:	00000000a80425fb
CapEff:	00000000a80425fb
CapBnd:	00000000a80425fb
CapAmb:	0000000000000000

$ docker run --rm alpine sh -c "apk add -q libcap && capsh --decode=..."
0x00000000a80425fb=cap_chown,cap_dac_override,cap_fowner,cap_fsetid,cap_kill,
cap_setgid,cap_setuid,cap_setpcap,cap_net_bind_service,cap_net_raw,cap_sys_chroot,
cap_mknod,cap_audit_write,cap_setfcap
```

```
$ docker run --rm --privileged alpine sh -c "grep Cap /proc/self/status"
CapInh:	0000000000000000
CapPrm:	000001ffffffffff
CapEff:	000001ffffffffff
CapBnd:	000001ffffffffff
CapAmb:	0000000000000000

$ capsh --decode=...
0x000001ffffffffff=cap_chown,...,cap_checkpoint_restore   (as 41, igual ao host)
```

O `--privileged` dá `0x1ffffffffff`, exactamente a máscara que o `cron` e o `CapBnd` da
shell tinham no Ex. 1: o conjunto completo do kernel. O default são 14
(`0xa80425fb`).

**Porque `--privileged` é root do host.** Um contentor é um processo normal no kernel do
host; as capabilities são verificadas pelo kernel do host, não por um kernel do
contentor. `--privileged` põe as 41 no permitted, effective e bounding — o mesmo que o
root do host tem — e acrescenta o resto: expõe todos os devices do host em `/dev`,
desliga o perfil AppArmor e o filtro seccomp por omissão, e deixa escrever em `/proc` e
`/sys`. Com `CAP_SYS_ADMIN` e um device do host chega-se ao disco do host (montar
`/dev/sda1` e ler `/etc/shadow`); `CAP_SYS_MODULE` carrega um módulo e corre código no
kernel. Duas que ele acrescenta, e o que cada uma abre:

- `CAP_SYS_ADMIN` — mount/umount, manipulação de namespaces e cgroups. É a que permite
  montar o disco do host dentro do contentor (ou usar o truque do `release_agent` do
  cgroup) e portanto sair do contentor.
- `CAP_DAC_READ_SEARCH` / `CAP_DAC_OVERRIDE` — ignorar as permissões de ficheiro na
  leitura/escrita; com o sistema de ficheiros do host montado, lê e escreve tudo.

(CAP_SYS_MODULE e CAP_SYS_PTRACE são as outras duas que tornam a frase "é root do host"
literal.)

O operador que corre `--privileged` a pensar que é seguro está a confundir
*visibilidade* com *privilégio*: acha que "está num contentor, logo está isolado". Os
namespaces limitam o que o processo **vê** (PIDs, mounts), não o que pode **fazer**; as
capabilities e o acesso aos devices são o que decide isso, e o `--privileged` retira
ambos os limites. É a mesma confusão do Lab 6: o contentor é uma fronteira de nomes, não
uma fronteira de autoridade.

### 3b — --user 1000

```
$ docker run --rm --user 1000 alpine sh -c "id; grep Cap /proc/self/status"
uid=1000 gid=0(root) groups=0(root)
CapInh:	0000000000000000
CapPrm:	0000000000000000
CapEff:	0000000000000000
CapBnd:	00000000a80425fb
CapAmb:	0000000000000000
```

O processo não segura nada (`CapPrm = CapEff = 0`), ao contrário do root do default, que
segura as 14 em permitted e effective. Mas o **tecto** continua a ser `0xa80425fb`, as
mesmas 14: o `--user 1000` só decidiu com que UID o processo começa, não baixou o
`CapBnd`. E o `CapBnd` é aplicado no `execve`, não tira o que já se tem — mas também não
impede que se ganhe de novo o que lá está.

**A rota que continua aberta é a do Ex. 2, dentro da imagem:** uma *file capability*. Se
a imagem tiver um binário com, por exemplo, `cap_dac_override+ep`, o `execve` desse
binário por um utilizador não-root calcula o permitted a partir do permitted do
ficheiro, limitado pelo `CapBnd` — e como `CAP_DAC_OVERRIDE` está no `CapBnd` default,
o processo passa a tê-la no permitted e, com o bit `+e`, também no effective. O que é
preciso existir na imagem é exactamente isso: um binário com a capability (ou um binário
setuid root, que é o mesmo problema pela outra via). Não é preciso ser root para a
*usar*, só para a *instalar* — e instalar é trabalho de quem constrói a imagem.

Com `CAP_DAC_OVERRIDE` o processo dentro do contentor lê e escreve qualquer ficheiro
independentemente do modo: `/etc/shadow` se existir, dados de outro utilizador, ou
qualquer caminho do host que esteja montado no contentor. Com `CAP_SETUID` podia passar
a uid 0 dentro do contentor; com `CAP_NET_RAW` forjar tráfego e fazer ARP spoofing na
rede do host.

Logo, "corre como non-root" não é "está em sandbox": diz só com que identidade o
processo **começa**. O que ele pode vir a ser depende do que o sistema de ficheiros lhe
oferece (file capabilities, setuid) e do tecto que lhe foi posto. Para o contentor ser
uma fronteira de autoridade é preciso baixar o `CapBnd` (`--cap-drop ALL`), garantir que
a imagem não traz binários privilegiados, e juntar seccomp/namespaces — o que o Lab 12
completa. Nota lateral: o `--user 1000` deixa `gid=0(root)`, portanto ficheiros
legíveis pelo grupo root continuam acessíveis; o uid sozinho não chega nem para o
grupo.

---

## Ex. 4 — o grant mínimo e o controlo negativo (Parte D)

Corrido em `~/ssc-lab7`, com `S="--sysctl net.ipv4.ip_unprivileged_port_start=1024"`
(postos os 1024 de volta, porque dentro do contentor o default é 0).

```
test 1  root, default caps                       BOUND :80 OK (uid=0)      rc=0
test 2  --user 1000, sem grant                   FAIL :80 denied (uid=1000) rc=1
test 3  --cap-drop ALL --cap-add NET_BIND_SERVICE BOUND :80 OK (uid=0)      rc=0
test 4  --cap-drop ALL, nada added               FAIL :80 denied (uid=0)    rc=1
```

Conjuntos, primeiro sem flags e depois com as flags do teste 3:

```
$ docker run --rm python:3.12-alpine python -c ".../proc/self/status..." | grep Cap
CapInh:	0000000000000000
CapPrm:	00000000a80425fb
CapEff:	00000000a80425fb
CapBnd:	00000000a80425fb
CapAmb:	0000000000000000

$ docker run --rm --cap-drop ALL --cap-add NET_BIND_SERVICE python:3.12-alpine ... | grep Cap
CapInh:	0000000000000000
CapPrm:	0000000000000400
CapEff:	0000000000000400
CapBnd:	0000000000000400
CapAmb:	0000000000000000

$ capsh --decode=0000000000000400
0x0000000000000400=cap_net_bind_service
```

### 4a

Resultados e UIDs: teste 1 liga como uid 0 (root, 14 caps default);
teste 2 falha como uid 1000; teste 3 liga como uid 0 com **uma** capability;
teste 4 falha como uid 0 com zero. O par 3/4 é o controlo negativo: sem o teste 4 só
se provou que uma configuração funciona, não que a menor não funciona.

O menor grant que liga é o do teste 3, numa linha: **drop ALL, add
NET_BIND_SERVICE**. As flags põem o `CapBnd` a `0x400` (só esse bit) e o permitted e
effective iguais a `0x400` porque o processo é root dentro do contentor. **Não cumpre o
objectivo de non-root**: liga como uid 0.

Comparado com o default (14), `--cap-drop ALL --cap-add NET_BIND_SERVICE` é mais
**apertado**: um bit em vez de catorze. "Começar do nada e acrescentar" é mais seguro do
que "começar do default e remover" porque o default não é um contrato: é uma lista que
o Docker pode acrescentar numa versão nova. Uma configuração por subtracção
(`--cap-drop X`) herda silenciosamente tudo o que for acrescentado ao default — no dia
em que o Docker passe a dar `CAP_FOO`, o contentor passa a tê-la sem ninguém mexer na
configuração. A construção por adição tem base vazia e resultado fixo: o que está
escrito é o que o processo tem, e é auditável. É a diferença entre uma allow-list e uma
deny-list, e a razão porque o default deve ser "nada" e não "o que o runtime achou
razoável".

### 4b

```
$ docker run --rm python:3.12-alpine sh -c 'cat /proc/sys/net/ipv4/ip_unprivileged_port_start'
0

$ docker run --rm -v "$PWD/captest.py:/captest.py" --user 1000 python:3.12-alpine python /captest.py 80
BOUND :80 OK (uid=1000)
rc=0

$ ... com $S ...
FAIL: bind :80 denied (uid=1000): [Errno 13] Permission denied
```

Um valor 0 em `ip_unprivileged_port_start` significa que **nenhum** port é reservado: a
partir do port 0 qualquer processo, com qualquer UID, pode fazer bind sem
`CAP_NET_BIND_SERVICE`. O port deixa de ser privilegiado e a capability deixa de ser o
que decide. O benefício prático para o Docker é poder correr serviços non-root em :80 e
:443 sem `--cap-add`, sem file capabilities e sem root — que é precisamente o modelo
que ele quer vender (e o que faz o rootless Docker funcionar); foi uma mudança
deliberada na 20.10.

Num contentor sem a flag, `CAP_NET_BIND_SERVICE` **não** decide se se pode ligar ao port
80: quem decide é o sysctl, que já disse que sim. Isto mostra o limite de raciocinar só
a partir de capabilities: o `CapEff` é uma das condições, não a política completa. O
mesmo conjunto de capabilities dá resultados diferentes conforme o `sysctl`, o
`CapBnd`, as file capabilities da imagem, o seccomp, o AppArmor e os namespaces. A
pergunta certa não é "que capability tem o processo?", é "que verificação o kernel faz
neste caminho, e quem lhe deu esse valor?".

---

## Ex. 5 — o serviço non-root com uma file capability (Parte E)

`$S` é outra vez definido nesta shell (`--sysctl net.ipv4.ip_unprivileged_port_start=1024`).

```
$ docker build -t lab7-capbind -f Dockerfile.capbind .
...
Successfully tagged lab7-capbind:latest

$ docker run --rm lab7-capbind sh -c 'getcap $(readlink -f /usr/local/bin/python3)'
/usr/local/bin/python3.12 cap_net_bind_service=ep
```

A minha imagem, como `--user 1000`, sem `--cap-add`:

```
$ docker run --rm -v "$PWD/captest.py:/captest.py" $S --user 1000 lab7-capbind python /captest.py 80
BOUND :80 OK (uid=1000)
rc=0

$ docker run --rm --user 1000 lab7-capbind python -c "...status..." | grep Cap
CapInh:	0000000000000000
CapPrm:	0000000000000400
CapEff:	0000000000000400
CapBnd:	00000000a80425fb
CapAmb:	0000000000000000
```

O controlo, as mesmas duas coisas na imagem `python:3.12-alpine` sem modificação:

```
$ docker run --rm -v "$PWD/captest.py:/captest.py" $S --user 1000 python:3.12-alpine python /captest.py 80
FAIL: bind :80 denied (uid=1000): [Errno 13] Permission denied
rc=1

$ docker run --rm --user 1000 python:3.12-alpine python -c "...status..." | grep Cap
CapInh:	0000000000000000
CapPrm:	0000000000000000
CapEff:	0000000000000000
CapBnd:	00000000a80425fb
CapAmb:	0000000000000000

$ docker run --rm python:3.12-alpine sh -c 'apk add -q libcap && getcap $(readlink -f /usr/local/bin/python3)'
      # (sem saída: não há file capability)
```

O grant não é do `captest.py`, é do interpretador — tudo o que ele correr herda-o:

```
$ docker run --rm -v "$PWD/captest.py:/captest.py" $S --user 1000 lab7-capbind python /captest.py 443
BOUND :443 OK (uid=1000)
$ docker run --rm $S --user 1000 lab7-capbind python -c 'import socket; ...; s.bind(("0.0.0.0",80))'
BOUND :80 by inline code
```

### 5a

Na minha imagem, `CapPrm = 0x0000000000000400`, que é o bit 10,
**`cap_net_bind_service`**. O `CapEff` é o mesmo (`0x400`) e o `CapAmb` é `0`
(`CapInh` também): a capability **não** chegou pelo ambient. Chegou pelo `execve`: o
ficheiro tem `cap_net_bind_service` no permitted (`+p`), o processo ganha-o no permitted
porque está no `CapBnd`, e o bit de effective do ficheiro (`+e`) faz com que o permitted
passe inteiro para effective. O ambient só herdaria o que estivesse no inheritable do
processo, que é zero.

`CapBnd` é `0xa80425fb` (as 14 default do Docker) nas **duas** imagens: o `--user 1000`
não mexe no tecto e a imagem também não. O que distingue as duas é só a file capability
no interpreter — a da imagem modificada tem-na, a stock não.

O grant **não** é só ao `captest.py`: é ao binário do interpretador. Qualquer script
(`/captest.py 443`) ou código inline (`python -c` a ligar :80) corre com
`cap_net_bind_service` no effective, porque a capability está no ficheiro
`/usr/local/bin/python3.12`. É a mesma propriedade (e o mesmo risco) que no Ex. 2: o
privilégio pertence ao executável, não ao que ele executa. Aqui o executável é o
interpretador inteiro, portanto o grant é tão largo quanto a linguagem.

---

## Ex. 6 — o grant é mínimo, o tecto não (Parte E)

```
$ $S --user 1000 --cap-drop ALL --cap-add NET_BIND_SERVICE lab7-capbind python /captest.py 80
BOUND :80 OK (uid=1000)
rc=0

$ docker run --rm --user 1000 --cap-drop ALL --cap-add NET_BIND_SERVICE lab7-capbind python -c "...status..." | grep Cap
CapInh:	0000000000000000
CapPrm:	0000000000000400
CapEff:	0000000000000400
CapBnd:	0000000000000400
CapAmb:	0000000000000000

$ docker run --rm -v "$PWD/captest.py:/captest.py" $S --user 1000 --cap-drop ALL lab7-capbind python /captest.py 80
exec /usr/local/bin/python: operation not permitted
rc=255
```

(no último caso o Python nem chega a correr; o `-c ...status...` correspondente dá o
mesmo `exec ... operation not permitted`.)

### 6a

UID 1000, e o serviço tem `CapPrm = CapEff = CapBnd = 0x400`, `CapAmb = 0`: o grant
vem da file capability e as flags só baixaram o tecto até coincidir com ele.

No último comando eu esperava ou um bind a falhar com `Permission denied`, ou — se
acreditasse que o `+e` chegasse — um bind a passar apesar do `--cap-drop ALL`. O que
aconteceu foi outra coisa: o `execve` foi recusado com **EPERM** antes de o
interpretador arrancar.

A explicação precisa dos dois factos:

1. **`+p` põe a capability no permitted do ficheiro**, e a transformação do `execve` é
   `P'(permitted) = (P(inheritable) & F(inheritable)) | (F(permitted) & P(bounding)) |
   P'(ambient)`. Com `--cap-drop ALL`, `P(bounding) = 0`, logo
   `F(permitted) & P(bounding) = 0x400 & 0 = 0`: o processo não obtém a capability.
2. **`+e` é o «effective bit» do ficheiro, um flag e não um conjunto**, e é isso que
   torna o binário *capability-dumb*. O capabilities(7), em «Safety checking for
   capability-dumb binaries», diz que ao executar um binário desses o kernel verifica
   se o processo obteve **todas** as permitted do ficheiro depois das transformações;
   se não obteve, «execve(2) fails with the error EPERM». Foi exactamente o que se viu.

Ou seja: o tecto não foi ignorado — foi aplicado no `execve`, e como o ficheiro se
declara `+e` (não sabe lidar com uma execução com menos privilégio do que pediu), o
kernel recusa-se a arrancar com ele em vez de o deixar correr capado.

Se a capability estivesse com **`+p` sozinho**, `F(effective) = 0`, o binário já não
seria capability-dumb e não haveria safety check: o `execve` passava. O permitted do
processo ficava a `0x400` (com o tecto default), mas o effective ficava
`P'(ambient) = 0` — porque a regra é `P'(effective) = F(effective) ? P'(permitted) :
P'(ambient)`. O Python corria, mas o bind continuava a falhar: a capability estava
guardada no permitted à espera de um `capset()` que o interpretador nunca faz. Com
`--cap-drop ALL` e `+p`, o permitted também ficava 0 e o resultado era o mesmo bind
recusado, só que sem o `exec` recusado. É a diferença entre «o programa não arranca
porque lhe falta o que pediu» e «arranca e o privilégio está lá, inactivo».

### 6b

O grant mínimo para um serviço **non-root** ligar a um port privilegiado é:
uid não-root + `cap_net_bind_service+ep` como file capability no binário que faz o bind
(aqui, o interpretador) + `CapBnd` reduzido a esse bit (`--cap-drop ALL --cap-add
NET_BIND_SERVICE`). É o que o 6.1 mede: `0x400/0x400/0x400`, uid 1000, bind OK.

Nenhuma combinação de `--cap-add`/`--cap-drop` sozinha o consegue produzir porque essas
flags, num processo non-root, só moldam o **bounding** — e o `execve` de um processo com
UID diferente de 0 limpa permitted e effective («if a process with nonzero user IDs
performs an execve(2) then any capabilities that are present in its permitted and
effective sets will be cleared»). O resultado é o do fim da Parte D: `--cap-drop ALL
--cap-add NET_BIND_SERVICE --user 1000` dá `CapPrm = CapEff = 0` e `CapBnd = 0x400`; a
capability está no tecto, que é o sítio de onde não se pode usá-la. Só o `execve` de um
ficheiro com a capability a pode pôr no permitted de um non-root — e é isso que o
`--cap-add` não faz. Ele funciona para o root do contentor apenas pelo caso especial
do uid 0 (`P'(permitted) = P(inheritable) | P(bounding)`, effective = permitted).

É exactamente o que o Ex. 2 fez no host, mudado para dentro da imagem: `setcap` no
binário, não uma flag do runtime. A flag tem o outro papel, o de baixar o tecto para
coincidir com o grant (6.1) — mas quem **dá** a capability a um non-root é o ficheiro.
Por isso a resposta certa para uma imagem é a que está no `Dockerfile.capbind`, e a
única forma de a obter com flags era aceitar o root dentro do contentor.

---

## Entregáveis (Lab report 3)

O enunciado só avalia, deste lab, as perguntas de preparação **P1/P2** e a
**Reflexão**; os exercícios não são entregues e ficam neste log como transcrição.

- `report3.tex` — nova secção «Lab 7 — capabilities: preparação» com P1 e P2, e novo
  anexo «Reflexão — Lab 7: capabilities» (293 palavras), ao lado dos do Lab 6.
- Título, cabeçalho e metadados do PDF passaram a «Bloco 3 — Lab 6 e Lab 7».
- `report3.pdf` recompilado (pdflatex, sem overfull boxes).

## Estado da VM

Ficaram na VM: `~/capbind`, `~/capbind_cap` (já sem capability), `~/lab7.zip`,
`~/pull-alpine.log`, `~/pull-python.log`, `~/ssc-lab7` e as imagens `alpine`,
`python:3.12-alpine`, `lab7-capbind`. O `~/capbind_suid` foi apagado no fim do Ex. 2.
O enunciado manda repor o snapshot `lab7-clean`; isso é feito no UTM.
