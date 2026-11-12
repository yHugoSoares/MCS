== 2.c -- Ler do TUN

#quote(block: true, attribution: [TP3 -- Task 2.c])[
  - On Host U, ping a host in the `192.168.53.0/24` network. What is printed
    out by the `tun.py` program? What has happened? Why?
  - On Host U, ping a host in the internal network `192.168.60.0/24`. Does
    `tun.py` print out anything? Why?
]

O programa (`tun_2c.py`, incluído no zip) é o do 2.b com um ciclo de leitura: lê do fd do TUN, converte os bytes num objecto `IP` do Scapy e imprime os campos de cada pacote. Como usamos `IFF_NO_PI`, o que sai do TUN é um pacote IP puro, sem header extra. Ignoro os pacotes não-IPv4 porque, assim que a interface sobe, o kernel também lá mete tráfego IPv6 link-local (router solicitations), que o dissector IPv4 do Scapy mostra todo trocado.

=== Primeira Experiência: ping para 192.168.53.1

#figure(image("logs/img/2c_ping.png", width: 100%), caption: [Ping para 192.168.53.1 (100% loss) e o que o `tun_2c.py` imprime.])

O programa imprime os três echo requests (`type=8`, `id=16`, `seq` 1 a 3, 84 bytes), um por ping, com `src=192.168.53.99` (o nosso TUN) e `dst=192.168.53.1`. O `ping` diz 100% loss porque o programa só lê: o pedido fica em user space e nunca é escrito nada de volta, logo o kernel nunca vê uma reply. Nos contadores vê-se isso mesmo: `TX` sobe (kernel -> programa) e `RX` fica a 0 (programa -> kernel).

Porque é que o pacote foi parar ao TUN? `192.168.53.0/24` é uma rede *diretamente ligada* ao `myInterface0`, então o kernel não precisa de gateway e manda o pacote direto para a interface (é ponto-a-ponto, nem há ARP). Tudo o que o kernel escreve num TUN é entregue ao processo que tem o fd aberto -- que é o que o ciclo imprime.

=== Segunda Experiência: ping para 192.168.60.5

#figure(image("logs/img/2c_eth0.png", width: 100%), caption: [Ping para o 192.168.60.5: não entra no TUN, sai pelo `eth0` (tcpdump). O log do `tun_2c.py` fica com as mesmas 7 linhas.])

Aqui o `tun_2c.py` não imprime nada (o log tem 7 linhas antes e depois). O `ip route get` explica: não há rota para `192.168.60.0/24`, por isso o kernel usa a default `via 10.9.0.1 dev eth0`, e o tcpdump no `eth0` apanha os echo requests a sair por lá. Ou seja, os pacotes não se perderam, foram pelo caminho errado: um TUN só recebe o tráfego que o *routing* lá manda. Para os 60.x irem pelo túnel é preciso `ip route add 192.168.60.0/24 dev myInterface0` (é o que falta nas tasks seguintes).

== 2.d -- Escrever no TUN

#quote(block: true, attribution: [TP3 -- Task 2.d])[
  Modify the `tun.py` code according to the following requirements:
  - After getting a packet from the TUN interface, if this packet is an ICMP
    echo request packet, construct a corresponding echo reply packet and write
    it to the TUN interface. Please provide evidence to show that the code
    works as expected.
  - Instead of writing an IP packet to the interface, write some arbitrary data
    to the interface, and report your observation.
]

O programa (`tun_2d.py`, no zip) é o do 2.c com escrita no TUN: para cada pacote lido, constrói um novo pacote e injeta-o no kernel com `os.write()`.

=== Primeira experiência: responder aos echo requests

Quando chega um echo request, construo a reply: troco src/dst, mudo o `type` de 8 para 0 e mantenho `id`, `seq` e payload. No fim reconstruo o pacote a partir dos bytes para o Scapy recalcular o `len` e os checksums -- se escrever o objecto sem isto, o kernel descarta a reply.

#figure(image("logs/img/2d_reply.png", width: 100%), caption: [O mesmo ping do 2.c, agora com 0% packet loss e replies do 192.168.53.1.])

O ping passa a `0% packet loss` e recebe `64 bytes from 192.168.53.1`, com `ttl=64` porque o header IP é novo (podia copiar o TTL original). Os contadores confirmam o mecanismo: `RX: 252 bytes / 3 packets` = exatamente as 3 replies de 84 bytes que escrevi. Ou seja, o kernel aceitou-as como pacotes *recebidos* na interface, apesar de o `192.168.53.1` não existir -- foram fabricadas em user space. 

=== Segunda Experiência: escrever dados arbitrários

Em vez de um pacote IP, o programa escreve 24 bytes arbitrários (`b"THIS IS NOT AN IP PACKET"`) no fd do TUN:

#figure(image("logs/img/2d_garbage.png", width: 100%), caption: [Escrita de 24 bytes arbitrários: `EINVAL` e `RX dropped` a subir; o ping continua a 100% loss.])

O `os.write()` falha com `EINVAL` e o ping continua a 100% loss, portanto não foi injetado nada; o kernel conta a tentativa como `dropped` no RX. O motivo é que o kernel valida o buffer como pacote IP antes de o entregar à stack: o nibble de versão do primeiro byte tem de ser 4 ou 6 (aqui é `0x54` = 5). Testei variando o primeiro byte e só `0x4x`/`0x6x` passam.

Se o buffer parecer IPv4 mas estiver inconsistente (ex.: `45 00 ...` com `len=0`), o write passa e é o `ip_rcv` que o descarta depois -- aí o contador `packets` sobe e o `dropped` também, e o erro só se vê nas estatísticas. Conclusão: ao contrário de um TAP (Ethernet), um TUN só aceita pacotes IP completos, o que é exatamente o que queremos para o túnel (o programa lê e escreve pacotes IP e pode metê-los diretamente no payload de UDP).