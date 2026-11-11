# TP3 - 2.c / 2.d

Relatório: `../report.typ` (Typst). Imagens: `img/`. Código: `tun_2c.py`, `tun_2d.py`,
`tun_2d_garbage.py`.

## O que são as imagens

As 4 figuras em `img/` **não** são prints do ecrã: são o output real das experiências,
capturado por SSH à VM (`transcritos/*.txt`) e renderizado em PNG pelo `tools/mkimg.py`
para ficar com aspecto de terminal. O conteúdo é o mesmo que aparece no ecrã.

Se o enunciado exigir prints genuínos, troca-as por capturas do ecrã:

1. Corre as experiências na VM (`make capture` ou os comandos do `scripts/shots.sh`).
2. No macOS: `⇧⌘4` (região) ou `⇧⌘5` (janela do VMware Fusion) — fica em `~/Desktop`.
3. Substitui o ficheiro em `img/` mantendo o nome (`2c_ping.png`, `2c_eth0.png`,
   `2d_reply.png`, `2d_garbage.png`) e recompila com `make pdf`.

Dentro da VM também dá com `gnome-screenshot -a -f ~/shot.png`.

## Regenerar

```bash
cd logs
make            # PNGs + ../report.pdf
make capture    # volta a correr tudo na VM (precisa de sshpass) e actualiza transcritos/
make clean
```

## Reproduzir à mão (na VM, em ~/TP3_Labsetup)

```bash
docker compose up -d
cp /caminho/tun_2c.py volumes/          # tun_2d.py, tun_2d_garbage.py também

# 2.c
docker exec -d client-10.9.0.5 bash -c "python3 -u /volumes/tun_2c.py > /volumes/tun2c.log 2>&1"
docker exec client-10.9.0.5 ping -c 3 -W 1 192.168.53.1   # 100% loss, mas aparece no log
docker exec client-10.9.0.5 cat /volumes/tun2c.log
docker exec client-10.9.0.5 ip route get 192.168.60.5     # via 10.9.0.1 dev eth0
docker exec client-10.9.0.5 ping -c 3 -W 1 192.168.60.5   # nao aparece nada no log

# 2.d
docker exec client-10.9.0.5 pkill -f tun_2c.py
docker exec client-10.9.0.5 ip link del myInterface0
docker exec -d client-10.9.0.5 bash -c "python3 -u /volumes/tun_2d.py > /volumes/tun2d.log 2>&1"
docker exec client-10.9.0.5 ping -c 3 -W 1 192.168.53.1   # 0% loss

# 2.d - dados arbitrarios
docker exec client-10.9.0.5 pkill -f tun_2d.py
docker exec client-10.9.0.5 ip link del myInterface0
docker exec -d client-10.9.0.5 bash -c "python3 -u /volumes/tun_2d_garbage.py > /volumes/tun2d_garbage.log 2>&1"
docker exec client-10.9.0.5 cat /volumes/tun2d_garbage.log   # OSError EINVAL + RX dropped
```

Notas: a interface chama-se `myInterface0` (prefixo do 2.a); cada script cria a interface e
sai, por isso é preciso `ip link del` entre execuções; o `docker exec -d` desliga o
processo do terminal, o output vai para o log em `/volumes`.
