### 1. Arquiteto de Infraestrutura (O "DevOps" e Tráfego Base)

Sem o trabalho deste elemento, o laboratório não arranca e a equipa não tem onde testar a firewall.

> Plano detalhado: [`plan/01-infra.md`](plan/01-infra.md). Esqueleto do laboratório: [`../lab/`](../lab/).

* **Criar o Laboratório:** Escrever o `docker-compose.yml` (ou ficheiros de VM) que liga o Atacante, a Firewall e o Serviço Protegido. Garantir que a firewall é o *gateway* obrigatório (roteamento correto) para que os pacotes passem efetivamente por lá.
* **Levantar os Alvos:** Instalar um Servidor Web e uma Base de Dados (ex: MySQL/PostgreSQL) na máquina vítima para servir de alvo aos ataques de camada de aplicação.
* **Gerar Tráfego Legítimo:** Escrever um script (ex: Python/Bash) que faça pedidos contínuos e normais ao Servidor Web e ao serviço de Ping. Isto é fundamental para provar o requisito obrigatório de "Legitimate Service" — mostrar que a firewall bloqueia o ataque sem bloquear os utilizadores normais.



### 2. Engenheiro Core da Firewall (Motor e Estado)

Este operacional constrói o código central da firewall (em Python com NetfilterQueue/Scapy, ou C). Não implementa regras específicas, constrói a fundação.

* **Interceção e Decisão:** Fazer o código intercetar os pacotes em trânsito e aplicar a política por omissão (*default policy*), decidindo de imediato se o pacote passa (`ACCEPT`) ou é bloqueado (`DROP`).


* **Gestão de Estado em Memória:** Criar tabelas e contadores temporários. A firewall precisa de memória para contar pacotes por IP (para os detetores de *flood*) e para rastrear sessões ativas (estado das ligações TCP).


* **Ações de Controlo:** Programar as funções de resposta (Bloquear, Rejeitar, Limitar Taxa, *Blocklist* temporária) que vão ser chamadas pelos colegas dos detetores.

### 3. Especialista Tático L3/L4 (Ataque + Detetores Volumétricos)

Fica com a automação dos ataques mais focados no esgotamento de recursos e varrimentos de rede, e escreve a lógica de deteção correspondente na firewall.

* **Varrimento e Fragmentação:** Criar o ataque de Port Scanning e o Ping of Death. Na firewall, adicionar os detetores que bloqueiam pacotes ICMP gigantes e penalizam IPs que acedem a demasiadas portas fechadas em pouco tempo.
* **Inundações (Floods):** Automatizar o SYN Flood, UDP Flood e ICMP/Ping Flood. Implementar os limiares de limitação de taxa (*rate limiting*) na firewall, consultando o sistema de estado criado pelo Engenheiro Core.
* **Manipulação de Controlo:** Automatizar o TCP RST Attack e o ICMP Redirect, escrevendo as regras que rejeitam a interrupção de sessões válidas e impedem a reconfiguração de rotas de rede.

### 4. Especialista Avançado L7 (Ataque + Detetores de Aplicação/Spoofing)

Fica responsável pelos ataques mais complexos, que exigem inspeção do conteúdo ou manipulação de protocolos de aplicação.

* **Ataques de Spoofing (Camada 2 e DNS):** Executar ARP Spoofing, DHCP Spoofing e DNS Spoofing. Na firewall, implementar defesas (como validação de respostas não solicitadas) ou, se atuar numa camada superior, justificar tecnicamente o motivo pelo qual a firewall L3/L4 não consegue intercetar a camada de ligação.
* **Amplificação e Esgotamento HTTP:** Implementar UDP Amplification/Reflection e HTTP Flood / Slowloris. Escrever os detetores que identificam picos de tráfego de amplificação e que controlam o número e o estado das sessões HTTP.
* **Injeção (SQLi) e Sequestro (Reverse Shell):** Executar SQL Injection e TCP Session Hijacking (com injeção de reverse shell). Tentar adicionar capacidades de Inspeção Profunda de Pacotes (DPI) na firewall para detetar as assinaturas (ex: comandos `UNION SELECT` no *payload* HTTP) e impedir a shell reversa.

### 5. Mestre da Telemetria (Monitorização e Registo de Provas)

O trabalho deste operacional é essencial para a nota final. Uma firewall cega que não prova que se defendeu perde os pontos do requisito de monitorização.

* **Sistema de Logs Estruturados:** Configurar a firewall para gerar um registo detalhado por cada ação de bloqueio (Timestamp, Ataque, IP Fonte, Ação, Razão).


* **Painel Visual (*Time-based View*):** Levantar uma plataforma de monitorização (ex: ELK Stack, Grafana) para processar os logs. O painel deve correlacionar em tempo real: o momento em que o ataque iniciou, a deteção, a ação da firewall e a manutenção do tráfego legítimo.


* **Documentação e README:** Escrever as instruções exatas de execução de todo o laboratório (para que os avaliadores o consigam replicar com um só clique) e fechar as matrizes de cobertura dos ataques.