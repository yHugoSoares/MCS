# Lab 8 — MAC, AppArmor e o sinal de detecção

Results log. Um bloco por exercício: o que se correu, o que se observou, o que prova, o
que vai para o Lab report 3.

Status: **Ex. 1–5 feitos**; relatório completo no `report3.tex`. Perfil descarregado e
removido da VM.

---

## Setup (pre-lab)

- VM `ssc-lab` (Ubuntu 24.04.5 LTS, aarch64). O snapshot `lab8-clean` é gerido no UTM
  (fora do guest); a VM ainda tinha o estado do Lab 7 quando comecei.
- Relógio do guest estava em 4 Nov (parado desde a sessão anterior), reposto com
  `sudo date -u -s "2026-11-11 12:17:30"` — importante para os `-ts recent` do auditd.
- AppArmor activo: `apparmor` active, 118 perfis carregados. `auditd` active.
- Ferramentas presentes: `aa-status`, `aa-genprof`, `aa-logprof`, `aa-complain`,
  `aa-enforce`, `ausearch` (apparmor-utils + auditd).
- A minha shell corre `unconfined` (`/proc/self/attr/current`). Os `sshd` com label
  `docker-default` que aparecem no `aa-status` são de contentores que estavam a correr,
  não da sessão.

---

## Ex. 1 — AppArmor no sistema (Parte A)

```
$ sudo aa-status
apparmor module is loaded.
118 profiles are loaded.
24 profiles are in enforce mode.
   /usr/bin/man
   /usr/lib/snapd/snap-confine
   docker-default
   lsb_release
   man_filter
   man_groff
   nvidia_modprobe
   ...
   rsyslogd
   tcpdump
   ubuntu_pro_apt_news
   unix-chkpwd
   unprivileged_userns
4 profiles are in complain mode.
   transmission-cli
   transmission-daemon
   transmission-gtk
   transmission-qt
0 profiles are in prompt mode.
0 profiles are in kill mode.
90 profiles are in unconfined mode.
   ...
4 processes have profiles defined.
4 processes are in enforce mode.
   /usr/sbin/sshd (6402) docker-default
   /usr/sbin/sshd (6464) docker-default
   /usr/bin/ssh-agent (8908) docker-default
   /usr/sbin/rsyslogd (786) rsyslogd

$ ls -l /etc/apparmor.d/
drwxr-xr-x  abi/  abstractions/  disable/  force-complain/  local/  rsyslog.d/
            tunables/
-rw-r--r--  usr.sbin.rsyslogd   usr.bin.man   usr.bin.tcpdump
-rw-r--r--  usr.lib.snapd.snap-confine.real   unprivileged_userns   ...
            (~100 perfis de aplicações: firefox, chrome, buildah, podman, ...)
```

(`docker-default` não está em `/etc/apparmor.d`: é gerado pelo `dockerd` e carregado
directamente.)

$ ps -eo label,comm | grep rsyslogd
rsyslogd (enforce)              rsyslogd

$ cat /etc/apparmor.d/usr.sbin.rsyslogd
# Last Modified: Sun Sep 25 08:58:35 2011
#include <tunables/global>
profile rsyslogd /usr/sbin/rsyslogd flags=(attach_disconnected) {
  #include <abstractions/base>
  #include <abstractions/nameservice>

  capability sys_tty_config,
  capability dac_override,
  capability dac_read_search,
  capability setuid,
  capability setgid,
  capability sys_nice,
  capability syslog,

  unix (receive) type=dgram,
  unix (receive) type=stream,

  /etc/rsyslog.conf r,
  /etc/rsyslog.d/ r,
  /etc/rsyslog.d/** r,
  /{,var/}run/rsyslogd.pid{,.tmp} rwk,
  ...
  /usr/sbin/rsyslogd mr,
  /usr/lib{,32,64}/{,@{multiarch}/}rsyslog/*.so mr,
  /dev/log rwl,
  /var/log/** rw,
  ...
  include if exists <rsyslog.d>
  #include <local/usr.sbin.rsyslogd>
}
```

### 1a — o que se vê no perfil do rsyslogd

Nada para escrever no relatório aqui; o objectivo é reconhecer as três espécies de
linha antes de escrever o meu perfil.

- **`capability ...`** — as capabilities (Lab 7) que o serviço pode usar:
  `syslog`, `dac_override`, `dac_read_search`, `setuid`, `setgid`, `sys_nice`,
  `sys_tty_config`. Qualquer outra é recusada, mesmo a root — é a ponte entre o Lab 7 e
  este.
- **caminho + letras** — `/etc/rsyslog.conf r` (só leitura), `/var/log/** rw` (leitura e
  escrita em tudo debaixo de `/var/log`), `/usr/sbin/rsyslogd mr` (map e read do próprio
  binário), `/dev/log rwl` (read/write/lock). O `**` é recursivo.
- **`include` / `#include`** — `#include <abstractions/base>` e
  `<abstractions/nameservice>` trazem regras de outro ficheiro; `include if exists
  <rsyslog.d>` inclui o directório de snippets `rsyslog.d` se existir;
  `#include <local/usr.sbin.rsyslogd>` é o override local. Aqui `#include` **não** é
  comentário — é regra; só as linhas que começam por `#` e não são `#include` é que são
  comentário.

Detalhe que interessa para o resto: o perfil do rsyslogd é um perfil **nomeado**
(`profile rsyslogd /usr/sbin/rsyslogd`), enquanto o meu vai ser um perfil por caminho,
sem nome. E o processo aparece com `(enforce)` no `ps`, que é como se vê o modo sem
`aa-status`.

---

## Ex. 2 — escrever e carregar o perfil mínimo (Parte B)

```
$ sudo cp /bin/cat /usr/local/bin/lab8svc
-rwxr-xr-x 1 root root 67928 Nov 11 12:18 /usr/local/bin/lab8svc

$ sudo tee /etc/apparmor.d/usr.local.bin.lab8svc >/dev/null <<'PROF'
#include <tunables/global>
/usr/local/bin/lab8svc {
  #include <abstractions/base>
  /usr/local/bin/lab8svc mr,
  /etc/hostname r,
}
PROF

$ sudo apparmor_parser -r /etc/apparmor.d/usr.local.bin.lab8svc   # rc=0
$ sudo aa-status | grep lab8svc
   /usr/local/bin/lab8svc
$ sudo grep lab8svc /sys/kernel/security/apparmor/profiles
/usr/local/bin/lab8svc (enforce)
```

### 2a — o perfil e o que ele permite

Perfil escrito (o de Part B, guardado tal como está):

```
#include <tunables/global>
/usr/local/bin/lab8svc {
  #include <abstractions/base>
  /usr/local/bin/lab8svc mr,
  /etc/hostname r,
}
```

Duas regras explícitas — o binário pode mapear-se e ler-se (`mr`) e pode ler
`/etc/hostname` (`r`) — mais o `#include <abstractions/base>`, que é política e não
comentário: acrescenta o que qualquer programa precisa para arrancar (bibliotecas do
loader, locale, `/dev/urandom`, escrita em `/dev/null` e no socket de log, parte de
`/proc`).

**Previsão (antes de correr):** `/etc/hostname` passa, porque tem regra `r`;
`/etc/shadow` é recusado, porque não tem regra nenhuma e o perfil está em enforce. O
facto de correr com `sudo` não muda nada: o DAC deixa passar (root), mas o MAC não.

```
$ sudo /usr/local/bin/lab8svc /etc/hostname
ssc-lab
exit=0

$ sudo /usr/local/bin/lab8svc /etc/shadow
/usr/local/bin/lab8svc: /etc/shadow: Permission denied
exit=1
```

Bateu certo com a previsão.

**Outro ficheiro que o `cat` como root lê e o perfil recusa:** `/etc/passwd`.

```
$ sudo cat /etc/passwd >/dev/null && echo "(root cat /etc/passwd: OK)"
(root cat /etc/passwd: OK)
$ sudo /usr/local/bin/lab8svc /etc/passwd
/usr/local/bin/lab8svc: /etc/passwd: Permission denied
exit=1
```

**`/proc` em `abstractions/base`.** Entradas concedidas (lidas do ficheiro):

- `@{PROC}/sys/kernel/version r`
- `@{PROC}/sys/kernel/ngroups_max r`
- `@{PROC}/sys/kernel/cap_last_cap r` (a do Ex. 1 do Lab 7)
- `@{PROC}/meminfo r`
- `@{PROC}/stat r`
- `@{PROC}/cpuinfo r`
- `@{PROC}/filesystems r`
- `@{PROC}/sys/vm/overcommit_memory r`
- `@{PROC}/@{pid}/{maps,auxv,status} r` — com `@{pid}` a ser o padrão de PIDs, portanto
  `/proc/self/{maps,auxv,status}` cai aqui (é o mesmo `/proc/<pid>/...`).

Aberto: `/proc/self/status`. Fechado: `/proc/self/mounts`.

```
$ sudo /usr/local/bin/lab8svc /proc/self/status | head -2
Name:	lab8svc
Umask:	0022
exit=0

$ sudo cat /proc/self/mounts >/dev/null && echo "(root cat: OK)"
(root cat: OK)
$ sudo /usr/local/bin/lab8svc /proc/self/mounts
/usr/local/bin/lab8svc: /proc/self/mounts: Permission denied
exit=1
```

Os resultados batem certo com a lista: `status` está no `abstractions/base`, `mounts`
não. É a diferença entre o que se pensa que o programa toca e o que a política permite —
que é precisamente o que um atacante procura.

---

## Ex. 3 — ler as negações e apertar o perfil (Parte C)

```
$ sudo /usr/local/bin/lab8svc /etc/hostname      # ssc-lab, exit=0
$ sudo /usr/local/bin/lab8svc /etc/shadow
/usr/local/bin/lab8svc: /etc/shadow: Permission denied
exit=1

$ sudo grep -a 'apparmor="DENIED"' /var/log/audit/audit.log | tail
type=AVC msg=audit(1794399687.541:3250): apparmor="DENIED" operation="open"
  class="file" profile="/usr/local/bin/lab8svc" name="/etc/shadow" pid=17879
  comm="lab8svc" requested_mask="r" denied_mask="r" fsuid=0 ouid=0
  FSUID="root" OUID="root"
```

A linha diz tudo o que o 4a vai pedir: `apparmor="DENIED"`, `operation="open"`,
`profile="/usr/local/bin/lab8svc"`, `name="/etc/shadow"`, `comm="lab8svc"`,
`pid=17879`, `requested_mask="r"`, `fsuid=0` (root) — e `fsuid=0` é o ponto: o DAC
deixou passar exactamente porque era root.

### 3a — MAC contra DAC

Um processo de root com as capabilities normais passa **todas** as verifica\c{c}\~oes
DAC e mesmo assim foi recusado. O perfil AppArmor pode proibir, por caminho, abrir,
ler, escrever, criar ou mapear ficheiros, usar capabilities, abrir sockets, fazer
mount, ptrace, e executar outros programas — independentemente do UID. Aqui proibiu
`open` de `/etc/shadow` a um processo com `fsuid=0`, que era exactamente o caso do
`backup-tool` no Lab 6.

Isso faz do MAC um controlo de outra natureza, n\~ao apenas "permiss\~oes de ficheiro
mais fortes": no DAC o dono do objecto decide (e o root pode sempre ignorar); no MAC a
pol\'itica \'e do sistema, est\'a ligada ao **programa** e n\~ao \`a identidade, e nem o
root nem o dono do ficheiro a podem contornar. A pergunta deixa de ser "quem \'e o
utilizador?" e passa a ser "que programa \'e este, e o que lhe foi permitido?".

O que o DAC faz bem e o MAC n\~ao substitui: a propriedade e a partilha de dados entre
utilizadores. `chmod`/`chown`/ACLs dizem quem \'e o dono e com quem se partilha um
ficheiro, sem precisar de uma pol\'itica por programa; o MAC n\~ao exprime "este
ficheiro \'e do hugo" nem resolve o problema de partilha — precisa de um perfil por
bin\'ario e de o manter.

Como distinguir um ficheiro de que o servi\c{c}o precisa de um que o atacante o obrigou
a alcan\c{c}ar: primeiro, a linha de base do comportamento normal (correr em complain e
ver o que ele abre a fazer o seu trabalho); depois, o que o pedido tem a ver com a
fun\c{c}\~ao e com a configura\c{c}\~ao do servi\c{c}o; e, por fim, a origem do caminho —
se vem de input do utilizador, se \'e uma travessia (`../`), se aparece depois de outro
pedido, e em que sequ\^encia. Um leitor de relat\'orios que abre `/etc/shadow` uma vez,
a seguir a um pedido externo, n\~ao "precisa" dele: foi levado l\'a.

### Least privilege: tirar a regra do /etc/hostname

```
$ sudo sed -i '\#^  /etc/hostname r,$#d' /etc/apparmor.d/usr.local.bin.lab8svc
$ cat /etc/apparmor.d/usr.local.bin.lab8svc
#include <tunables/global>
/usr/local/bin/lab8svc {
  #include <abstractions/base>
  /usr/local/bin/lab8svc mr,
}
$ sudo apparmor_parser -r /etc/apparmor.d/usr.local.bin.lab8svc    # rc=0
$ sudo /usr/local/bin/lab8svc /etc/hostname
/usr/local/bin/lab8svc: /etc/hostname: Permission denied
exit=1
```

A leitura passou a ser recusada. Removi a regra porque o trabalho de um leitor de
relat\'orios n\~ao inclui `/etc/hostname`: a regra existia para a demonstra\c{c}\~ao, e
cada caminho permitido a mais \'e superf\'icie de ataque a menos.

C\'opia guardada antes de mexer mais no ficheiro:
`sudo cp /etc/apparmor.d/usr.local.bin.lab8svc ~/lab8-final-profile`
(114 bytes, `student:student`).

### 3b — o que o perfil final impede um atacante de fazer

Impede-o de **executar outro programa**: o perfil final n\~ao tem nenhuma regra de
execu\c{c}\~ao, portanto um atacante que tomasse o servi\c{c}o n\~ao conseguia lan\c{c}ar
uma shell (`/bin/sh`), um `cat` ou um `curl` para ir buscar a segunda fase. E impede a
leitura de tudo o que est\'a fora do `abstractions/base` — `/etc/shadow`,
`/etc/passwd`, chaves SSH, `/proc/self/mounts` — e a escrita de ficheiros (s\'o
`/dev/null` e o socket de log v\^em do base). A shell \'e a que ele quer mais: sem
exec, o compromisso fica preso ao bin\'ario.

### 3c — complain mode

```
$ sudo aa-complain /usr/local/bin/lab8svc
Setting /usr/local/bin/lab8svc to complain mode.
$ sudo grep lab8svc /sys/kernel/security/apparmor/profiles
/usr/local/bin/lab8svc (complain)
$ sudo /usr/local/bin/lab8svc /etc/shadow >/dev/null     # conteúdo omitido
exit=0

$ sudo grep -a 'apparmor="ALLOWED"' /var/log/audit/audit.log | tail -2
type=AVC msg=audit(1794399696.664:3330): apparmor="ALLOWED" operation="open"
  class="file" profile="/usr/local/bin/lab8svc" name="/etc/shadow" pid=18013
  comm="lab8svc" requested_mask="r" denied_mask="r" fsuid=0 ouid=0
  FSUID="root" OUID="root"

$ sudo aa-enforce /usr/local/bin/lab8svc
$ sudo /usr/local/bin/lab8svc /etc/shadow >/dev/null
exit=1
$ sudo grep -a 'apparmor="DENIED"' /var/log/audit/audit.log | grep -a shadow | tail -1
type=AVC ... apparmor="DENIED" ... name="/etc/shadow" pid=18024 ...
```

Em complain a leitura **aconteceu** (`exit=0`) e a linha diz `apparmor="ALLOWED"`; em
enforce foi **parada** (`exit=1`) e a linha diz `DENIED`. A palavra no log \'e o que
distingue os dois — e note-se que a linha ALLOWED mant\'em `denied_mask="r"`: o kernel
registou o que *teria* negado.

Para um perfil de um servi\c{c}o que n\~ao escrevi, carregava primeiro em **complain**:
vejo o que ele pede sem o partir, e s\'o passo a enforce quando a linha de base estiver
est\'avel. Mudo quando o servi\c{c}o j\'a corre sem nega\c{c}\~oes inesperadas e a
pol\'itica est\'a revista. O risco que aceito \'e o de o perfil estar errado e n\~ao
proteger nada durante esse tempo — complain registra mas n\~ao impede, e uma
nega\c{c}\~ao que eu n\~ao leia \'e s\'o ru\'ido.

### 3d — executar outro programa

```
run() { sudo aa-exec -p /usr/local/bin/lab8svc -- /usr/bin/dash \
          -c '/usr/bin/cat /etc/hostname 2>/dev/null; echo rc=$?'; }

run                                       # sem regra de exec      -> rc=126

# linha acrescentada:
  /usr/bin/cat Px,
run                                       # Px sem perfil para cat -> rc=126
$ sudo aa-status | grep -i cat            # (nada: não há perfil para o cat)

# linha mudada:
  /usr/bin/cat ix,
run                                       # ix, herda o perfil      -> rc=1
```

**3d-i.** Os tr\^es valores: `126`, `126`, `1`. A linha final \'e
`/usr/bin/cat ix,`: o caminho do programa e o modo. `ix` \'e *inherit-execute* — o
`cat` corre confinado pelo **mesmo** perfil do `lab8svc`, herdando as suas regras. `Px`
d\'a 126 porque exige um perfil pr\'oprio para `/usr/bin/cat`, e n\~ao existe nenhum
(`aa-status | grep cat` n\~ao mostra nada): a transi\c{c}\~ao falha com EACCES e a shell
reporta 126 ("encontrou mas n\~ao pode executar"). O \'ultimo valor, `1`, mostra o que o
`cat` herda: corre (a execu\c{c}\~ao foi permitida pelo `ix`), mas continua sujeito ao
perfil do `lab8svc`, que j\'a n\~ao permite ler `/etc/hostname` — falha com o c\'odigo
do pr\'oprio `cat`, n\~ao com o da shell. A restri\c{c}\~ao passou para o filho.

**3d-ii — a armadilha do symlink.**

```
# regra mudada de /usr/bin/cat para /bin/cat
  /bin/cat ix,
$ sudo apparmor_parser -r /etc/apparmor.d/usr.local.bin.lab8svc
parser rc=0                      # o parser não se queixa
$ run                            # a correr /usr/bin/cat
rc=126
$ readlink -f /bin/cat
/usr/bin/cat
```

O `rc` passou de `1` para `126`: a regra deixou de casar. O parser aceita
`/bin/cat` sem aviso, mas o kernel resolve o caminho para `/usr/bin/cat` e compara com
esse; como a regra diz `/bin/cat`, n\~ao casa com nada. Chamar o `cat` pelo caminho da
regra tamb\'em n\~ao ajuda:

```
$ run2() { ... -c '/bin/cat /etc/hostname 2>/dev/null; echo rc=$?'; }
$ run2
rc=126
```

O kernel continua a ver `/usr/bin/cat`; o nome que se escreve na shell n\~ao \'e o
caminho que a pol\'itica v\^e. O mesmo para a shell: `readlink -f /bin/sh` d\'a
`/usr/bin/dash`. Uma regra escrita para `/bin/sh` controla o *symlink*, n\~ao o
bin\'ario que l\'a est\'a; para controlar as shells o autor tem de escrever as regras
para os caminhos reais (`/usr/bin/dash`, `/usr/bin/bash`, ...), porque \'e isso que o
kernel compara. E se o alvo do symlink mudar, a regra deixa de cobrir o que se julgava
coberto.

**3d-iii.** Com `ix` para uma shell, o atacante que entra nessa shell fica com **todas
as permiss\~oes que o perfil do servi\c{c}o d\'a** — a shell corre dentro da mesma
caixa, e n\~ao numa mais pequena: pode ler e escrever tudo o que o perfil permite, com
a identidade e os acessos do servi\c{c}o, mas n\~ao ganha nada fora dele.

---

## Ex. 4 — a nega\c{c}\~ao como sinal de detec\c{c}\~ao (Parte D)

```
$ sudo /usr/local/bin/lab8svc /etc/shadow
/usr/local/bin/lab8svc: /etc/shadow: Permission denied
exit=1

$ sudo ausearch -m AVC -ts recent
<no matches>
ausearch rc=1

$ sudo dmesg | grep -i apparmor
[    3.054587] audit: type=1400 ... apparmor="STATUS" operation="profile_load"
  profile="unconfined" name="balena-etcher" pid=455 comm="apparmor_parser"
[... só linhas STATUS do arranque ...]
# 9 linhas STATUS, 0 com apparmor="DENIED"

$ sudo grep -a 'apparmor="DENIED"' /var/log/audit/audit.log | grep -a shadow | tail
type=AVC msg=audit(1794399868.918:3547): apparmor="DENIED" operation="open"
  class="file" profile="/usr/local/bin/lab8svc" name="/etc/shadow" pid=18326
  comm="lab8svc" requested_mask="r" denied_mask="r" fsuid=0 ouid=0
  FSUID="root" OUID="root"

$ sudo grep lab8svc /sys/kernel/security/apparmor/profiles
/usr/local/bin/lab8svc (enforce)
```

Nem o `ausearch` nem o `dmesg` mostram a nega\c{c}\~ao. O `ausearch -m AVC` procura
registos AVC no formato do SELinux e salta os do AppArmor (falta-lhes `tclass=`); o
`dmesg` n\~ao a tem porque, com o auditd a correr, o kernel entrega os registos ao
auditd em vez de os imprimir no message buffer. Quem confiasse em qualquer um dos dois
conclu\'ia ``n\~ao houve nega\c{c}\~oes'' enquanto o servi\c{c}o estava a ser sondado.

### 4a — nota de defensor

| campo | resposta |
|---|---|
| Evid\^encia: a linha e os valores de `apparmor`, `operation`, `profile`, `name`, `comm`, `pid` | `apparmor="DENIED"`, `operation="open"`, `profile="/usr/local/bin/lab8svc"`, `name="/etc/shadow"`, `comm="lab8svc"`, `pid=18326` (linha acima) |
| O que foi tentado | O processo `lab8svc` (pid 18326, `comm=lab8svc`, a correr com `fsuid=0`/root) tentou abrir `/etc/shadow` para leitura (`requested_mask="r"`) |
| O que o travou | O perfil `/usr/local/bin/lab8svc`, em **enforce** (confirmado em `/sys/kernel/security/apparmor/profiles`) |
| Como o encontrei | Tentei `ausearch -m AVC -ts recent` (sem resultados) e `dmesg \| grep -i apparmor` (s\'o STATUS do arranque); funcionou `grep -a 'apparmor="DENIED"' /var/log/audit/audit.log` |
| O que a linha n\~ao diz | Porqu\^e, nem quem o mandou fazer: n\~ao tem a linha de comando, o processo pai, a sess\~ao do utilizador, o pedido externo que levou a isto, nem se era ataque ou erro de configura\c{c}\~ao. N\~ao diz o que foi lido (foi negado, mas n\~ao diz o que *teria* sido), nem o que aconteceu antes ou depois, nem quantas tentativas houve noutros caminhos |

Antes de um incidente, para saber se a ferramenta em que penso confiar mostra mesmo este
tipo de evento: provocava uma nega\c{c}\~ao conhecida --- correr o bin\'ario confinado
contra um ficheiro que o perfil n\~ao permite --- e confirmava que (a) a ferramenta
mostra essa linha, (b) com o evento garantido, e (c) que uma resposta vazia corresponde
a "n\~ao houve evento" e n\~ao a "a ferramenta n\~ao v\^e este tipo". No caso do
`ausearch`, isso teria mostrado logo que ele n\~ao v\^e AppArmor.

### 4b — detec\c{c}\~ao e preven\c{c}\~ao

Em **enforce** ganho a preven\c{c}\~ao --- a leitura foi parada, o dado n\~ao saiu --- e
perco a observa\c{c}\~ao do que o atacante faria a seguir; o log diz `DENIED` e nada
mais. Em **complain** ganho a observa\c{c}\~ao completa (o acesso aconteceu e foi
registado como `ALLOWED`, com o `denied_mask` que *teria* sido aplicado) e perco o
controlo: o dado foi lido, a escrita foi feita, o dano \'e real.

Preciso dos dois porque s\~ao metades diferentes do mesmo trabalho: o controlo que
bloqueia impede o dano mas n\~ao me diz que estou a ser atacado; o log diz-me que estou a
ser atacado mas, sem o controlo, s\'o depois do dano. Um SIEM ou uma pessoa a ler o log
precisa do registo; a pol\'itica precisa de bloquear. Al\'em disso, os `DENIED` s\~ao o
que permite afinar o perfil e o que serve de evid\^encia depois --- e um ataque que falha
silenciosamente tamb\'em \'e informa\c{c}\~ao: diz que algu\'em est\'a a tentar.

---

## Ex. 5 — a vista cross-platform (Parte E, escrita)

Sem hands-on; o texto entregue est\'a no `report3.tex` (secção «Lab 8 — a vista
cross-platform (5)»). Resumo do que ficou escrito, pelos dois casos medidos:

| mecanismo | como impede a leitura de `/etc/shadow` | quem escreve | o problema do 3d-ii? |
|---|---|---|---|
| SELinux | dom\'inio do processo vs tipo do ficheiro (`shadow_t`); nega com EACCES e regista AVC com `tclass=file` | administrador/distribui\c{c}\~ao (m\'odulos de pol\'itica) | n\~ao: o label est\'a no inode, os dois caminhos do `cat` s\~ao o mesmo ficheiro |
| FreeBSD jails | o jail s\'o v\^e a sub\'arvore montada como raiz; o shadow do host n\~ao existe l\'a | administrador (config do jail, mounts) | n\~ao da mesma forma: n\~ao h\'a regras por caminho; symlink resolve dentro da raiz |
| pledge/unveil | o programa declara as paths e syscalls; path n\~ao unveilada d\'a ENOENT/EACCES | o programador (auto-restri\c{c}\~ao) | pode: \'e por nome, mas o programa unveila o que abre e fecha a lista |
| Windows IL/tokens | DACL do SAM s\'o d\'a SYSTEM; MIC imp\~oe no-write-up | administrador/SO (ACLs, labels) | n\~ao: a decis\~ao \'e sobre o objecto (descriptor), n\~ao o nome |

Ideia comum: os cinco tiram a decis\~ao da identidade do utilizador e p\~oem-na numa
pol\'itica que o processo n\~ao reescreve (perfil, label, namespace, promessas, token) —
o monitor de refer\^encia.

AppArmor por caminho: **f\'acil** porque se escreve em caminhos, por programa, sem
relabelar nem tocar no c\'odigo; **fr\'agil** porque o caminho \'e a identidade e o mesmo
ficheiro tem v\'arios nomes (symlinks, hardlinks, bind mounts, renames) — a regra para
`/bin/cat` n\~ao casou e o parser n\~ao avisou.

---

## Entregáveis (Lab report 3)

- `report3.tex` inclui agora, do Lab 8: P1/P2, 2a, 3a, o passo de least privilege com o
  perfil final, 3b, 4a (nota de defensor + verifica\c{c}\~ao pr\'evia da ferramenta), 4b,
  Parte E e a reflex\~ao (281 palavras).
- Perfil final guardado fora da VM: `lab8-final-profile`.
- `report3.pdf` recompilado: 12 p\'aginas, sem overfull boxes.

## Limpeza

```
$ sudo apparmor_parser -R /etc/apparmor.d/usr.local.bin.lab8svc
$ sudo rm -f /etc/apparmor.d/usr.local.bin.lab8svc /usr/local/bin/lab8svc
$ rm -f ~/lab8-final-profile
```

Perfil descarregado, ficheiros removidos. Fica a faltar repor o snapshot `lab8-clean`
no UTM (ac\c{c}\~ao do utilizador).
